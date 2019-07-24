# -*- coding: utf-8 -*-

import json
import openfonacide.settings as settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.urlresolvers import reverse
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.core.exceptions import ObjectDoesNotExist
from django.db import connection
from django.db import transaction
from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.template import RequestContext, Context
from django.template.loader import get_template
from django.utils.datastructures import MultiValueDictKeyError
from django.views.generic import View, TemplateView
from rest_framework.decorators import detail_route
from rest_framework import filters
from rest_framework.generics import ListAPIView, ListCreateAPIView, get_object_or_404
from django.http import Http404, JsonResponse
from rest_framework import viewsets
from rest_framework import pagination
from rest_framework.response import Response
from rest_framework import permissions, authentication
from datetime import datetime

from django.contrib.auth.models import User
from models import *
from openfonacide.forms import ReporteForm

from openfonacide.utils import dictfetch, escapelike
from openfonacide.serializers import *
from openfonacide import jsonh as JSONH

"""
ViewSets for API
"""


class MultipleFieldLookupMixin(object):
    """
    Apply this mixin to any view or viewset to get multiple field filtering
    based on a `lookup_fields` attribute, instead of the default single field filtering.
    """

    def get_object(self):
        queryset = self.get_queryset()  # Get the base queryset
        queryset = self.filter_queryset(queryset)  # Apply any filter backends
        filter = {}
        for field in self.lookup_fields:
            if field in self.kwargs:
                filter[field] = self.kwargs[field]
            else:
                if field == 'periodo' or field == 'anio':
                    filter[field] = u'2014'
        return get_object_or_404(queryset, **filter)  # Lookup the object


class PaginadorEstandard(pagination.LimitOffsetPagination):
    default_limit = 100


class OpenFonacideViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    pagination_class = PaginadorEstandard
    filter_backends = (filters.DjangoFilterBackend,)


class EstablecimientoViewSet(OpenFonacideViewSet):
    """
    Este `Endpoint` muestra los establecimientos escolares del MEC
    y permite filtrar los resultados por los campos
    *codigo_establecimiento*, *anio*, y *uri*

    Nota: el parámetro *anio* se refiere al año se utilizó este nombre
    para evitar problemas de codificación

    """
    serializer_class = EstablecimientoSerializer
    queryset = Establecimiento.objects.all()
    filter_fields = ('codigo_establecimiento', 'anio', 'uri', 'nombre_departamento', 'nombre_distrito')
    lookup_field = 'codigo_establecimiento'
    lookup_fields = ('codigo_establecimiento', 'anio',)

    @detail_route(methods=['get'], url_path='prioridad')
    def prioridad(self, request, codigo_establecimiento=None):
        prioridad_view = PrioridadAPIViewDetail()
        prioridad = prioridad_view.get_object(codigo_establecimiento=codigo_establecimiento)
        p_ser = PrioridadSerializer(prioridad)
        if request.GET.get('format') is 'jsonh':
            print request.GET['format']
            return Response(JSONH.pack(p_ser.data))
        return Response(p_ser.data)


class TemporalListView(ListCreateAPIView):
    model = Temporal
    serializer_class = TemporalSerializer
    queryset = Temporal.objects.all()

    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        data_list = request.data
        respuesta_list = list()
        for data in data_list:
            try:
                llamado = data['id_llamado']
                institucion = data['codigo_institucion']
                periodo = data['periodo']
            except MultiValueDictKeyError as e:
                return JsonResponse({"mensaje": "Faltan parámetros : " + e.message, "look": request.data}, status=500)

            try:
                p = Planificacion.objects.get(id_llamado=llamado, anio=periodo)
                i = Institucion.objects.get(codigo_institucion=institucion, periodo=periodo)
            except ObjectDoesNotExist as e:
                # Teóricamente la planificación e institución dadas debe existir en la BD
                # Probablemente es un error con los datasets
                return JsonResponse({"mensaje": e.message}, status=500)

            i.planificaciones.add(p)

            set_a = Adjudicacion.objects.filter(id_llamado=llamado)
            for a in set_a:
                i.adjudicaciones.add(a)

            i.save()
            Temporal.objects.filter(id=data['id']).delete()
            respuesta_list.append(data['indice'])

        return JsonResponse({"mensaje": "Creado existosamente", 'resultado': respuesta_list}, status=200)


class UnlinkAPIView(ListAPIView):
    model = Institucion
    serializer_class = InstitucionUnlinkSerializer
    queryset = Institucion.objects.filter(planificaciones__isnull=False)
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        data = request.data
        respuesta_list = list()

        for d in data:
            try:
                id_institucion = d['id']
                id_planificacion = d['idp']
            except MultiValueDictKeyError as e:
                return JsonResponse({"mensaje": "Faltan parámetros : " + e.message, "look": request.data}, status=500)

            try:
                i = Institucion.objects.get(id=id_institucion)
                p = Planificacion.objects.get(id=id_planificacion)
            except ObjectDoesNotExist as e:
                return JsonResponse({"mensaje": e.message}, status=500)

            i.planificaciones.remove(p)

            i.save()
            respuesta_list.append(d['indice'])

        return JsonResponse({"mensaje": "Creado existosamente", 'resultado': respuesta_list}, status=200)


class InstitucionViewSet(MultipleFieldLookupMixin, OpenFonacideViewSet):
    serializer_class = InstitucionSerializer
    queryset = Institucion.objects.all()
    filter_fields = (
        'codigo_institucion', 'codigo_establecimiento', 'periodo', 'uri_institucion', 'nombre_departamento',
        'nombre_distrito'
    )
    lookup_field = 'codigo_institucion'
    lookup_fields = ('codigo_institucion', 'periodo')


class EspacioViewSet(OpenFonacideViewSet):
    serializer_class = EspacioSerializer
    queryset = Espacio.objects.all()
    filter_fields = (
        'periodo', 'codigo_establecimiento', 'codigo_institucion', 'nombre_espacio',
        'tipo_requerimiento_infraestructura'
    )
    lookup_field = 'codigo_establecimiento'
    lookup_fields = ('codigo_establecimiento', 'periodo',)


class SanitarioViewSet(OpenFonacideViewSet):
    serializer_class = SanitarioSerializer
    queryset = Sanitario.objects.all()
    filter_fields = ('periodo', 'codigo_establecimiento', 'codigo_institucion', 'tipo_requerimiento_infraestructura')
    lookup_field = 'codigo_establecimiento'
    lookup_fields = ('codigo_establecimiento', 'periodo',)


class MobiliarioViewSet(OpenFonacideViewSet):
    serializer_class = MobiliarioSerializer
    queryset = Mobiliario.objects.all()
    filter_fields = ('periodo', 'codigo_establecimiento', 'codigo_institucion')
    lookup_field = 'codigo_establecimiento'
    lookup_fields = ('codigo_establecimiento', 'periodo',)


class ServicioBasicoViewSet(OpenFonacideViewSet):
    serializer_class = ServicioBasicoSerializer
    queryset = ServicioBasico.objects.all()
    filter_fields = ('periodo', 'codigo_establecimiento')
    lookup_field = 'codigo_establecimiento'
    lookup_fields = ('codigo_establecimiento', 'periodo',)


class DummyPrioridad(object):
    espacio = None
    mobiliario = None
    sanitario = None
    servicio = None


class PrioridadAPIViewDetail(viewsets.views.APIView):
    """
    Vista para listar las prioridades, y servicios de un establecimiento
    en especifico, dado un codigo de establecimiento
    """
    permission_classes = (permissions.IsAuthenticated,)

    def get_object(self, codigo_establecimiento):
        prioridad = DummyPrioridad()
        not_found = 0

        try:
            Establecimiento.objects.get(codigo_establecimiento=codigo_establecimiento)
        except Establecimiento.DoesNotExist:
            return Http404

        try:
            prioridad.espacio = Espacio.objects.filter(codigo_establecimiento=codigo_establecimiento)
        except Espacio.DoesNotExist:
            not_found += 1
        try:
            prioridad.mobiliario = Mobiliario.objects.filter(codigo_establecimiento=codigo_establecimiento)
        except Mobiliario.DoesNotExist:
            not_found += 1
        try:
            prioridad.sanitario = Sanitario.objects.filter(codigo_establecimiento=codigo_establecimiento)
        except Sanitario.DoesNotExist:
            not_found += 1
        try:
            prioridad.servicio = ServicioBasico.objects.filter(codigo_establecimiento=codigo_establecimiento)
        except ServicioBasico.DoesNotExist:
            not_found += 1

        if not_found == 4:
            return Http404

        return prioridad

    def get(self, request, codigo_establecimiento, format=None):
        prioridad = self.get_object(codigo_establecimiento)
        serializer = PrioridadSerializer(prioridad)
        if format == "jsonh":
            return Response(JSONH.pack(serializer.data))
        return Response(serializer.data)


class PrioridadAPIView(viewsets.views.APIView):
    """
    Vista para listar todas las prioridades, espacios (aulas, otros)
    mobiliarios, sanitarios. Y ademas los serivicios basicos
    """
    permission_classes = (permissions.IsAuthenticated,)
    # queryset = DummyPrioridad()

    def get_queryset(self):
        queryset = DummyPrioridad()
        queryset.espacio = Espacio.objects.all()
        queryset.mobiliario = Mobiliario.objects.all()
        queryset.sanitario = Sanitario.objects.all()
        queryset.servicio = ServicioBasico.objects.all()
        return queryset

    def get(self, request, format=None):
        """
        Retorna la lista de todas las prioridades y servicios
        """
        prioridad_serializada = PrioridadSerializer(self.get_queryset())

        if format == "json":
            return JsonResponse(prioridad_serializada.data, safe=False)

        if format == "jsonh":
            return JsonResponse(JSONH.pack(prioridad_serializada.data), safe=False)

        return Response(prioridad_serializada.data)


class PartialGroupView(TemplateView):
    """
    Utilizada para los templates de AngularJS
    """

    def get_context_data(self, **kwargs):
        context = super(PartialGroupView, self).get_context_data(**kwargs)
        # update the context
        return context


class Index(View):
    def get(self, request, *args, **kwargs):
        return render_to_response('index-nuevo.html', context_instance=RequestContext(request))


class Recuperar(View):
    def get(self, request, *args, **kwargs):
        return render_to_response('index-nuevo.html', context_instance=RequestContext(request))

    def post(self, request, *args, **kwargs):
        method = request.POST.get('_method')
        _query = request.GET.copy()
        print request.REQUEST.__str__();
        print _query;
        _query.pop("error", None)
        _query.pop("message", None)
        _query.pop("success", None)
        if method == 'PUT':
            password = request.POST.get('password')
            password_confirm = request.POST.get('password_confirm')
            email = request.GET.get('email')
            token = request.GET.get('token')
            print email
            if password == password_confirm:
                try:
                    user = User.objects.get(email=email)
                    token_gen = PasswordResetTokenGenerator()
                    if token_gen.check_token(user, token):
                        user.set_password(password)
                        user.save()
                        _query['success'] = 'password_changed'
                        _query['message'] = 'Tu password ha sido cambiado!'
                        # redirect ?success=password_changed
                    else:
                        _query['error'] = 'invalid_token'
                        _query['message'] = 'Esta url ha caducado o es inválida!'
                        # redirect ?error=invalid_token
                except ObjectDoesNotExist:
                    # redirect ?error=user_does_not_exist
                    _query['error'] = 'user_does_not_exist'
                    _query['message'] = 'El usuario no existe!'
            else:
                # redirect ?error=password_missmatch
                _query['error'] = 'password_missmatch'
                _query['message'] = 'Las contraseñas no coinciden!'
                pass
        else:
            email = request.POST.get('email')

            user = User.objects.get(email=email)
            if user:
                token_gen = PasswordResetTokenGenerator()
                token = token_gen.make_token(user)
                print user.username
                ctx = {
                    "name": user.username,
                    "url": request.build_absolute_uri(reverse('recuperar_pass')) + '?token=' + token + '&email=' + email
                }
                mensaje = get_template('registration/mail.recuperar.html').render(Context(ctx))
                to = [email]
                mail = EmailMessage('Recuperar Contraseña',
                                    mensaje,
                                    to=to,
                                    from_email=settings.EMAIL_HOST_USER)
                mail.content_type = 'html'
                mail.send()

            _query['success'] = 'email_sent'
            _query['message'] = 'Se ha enviado un correo con las instrucciones!'
            # redirect ?success=email_sent
        return redirect(reverse('recuperar_pass') + '?' + _query.urlencode())


class EstablecimientoController(View):
    def get(self, request, *args, **kwargs):
        _md5 = request.GET.get('md5')
        if _md5:
            cursor = connection.cursor()
            cursor.execute(
                'select md5(CAST((array_agg(es.* order by es.id)) AS text)) from openfonacide_establecimiento es')
            result = cursor.fetchone()[0]
            return JsonResponse({"hash": result})

        codigo_establecimiento = kwargs.get('codigo_establecimiento')
        short = request.GET.get('short')
        query = request.GET.get('q')
        anio = request.GET.get('anio')
        if not anio:
            anio = '2014'
        if short is not None:
            if codigo_establecimiento:
                establecimiento = EstablecimientoSerializerShort(
                    Establecimiento.objects.get(codigo_establecimiento=codigo_establecimiento, anio=anio))
            else:
                if query is not None:
                    establecimiento = EstablecimientoSerializerShort(
                        Establecimiento.objects.filter(nombre__icontains=query, anio=anio) |
                        Establecimiento.objects.filter(direccion__icontains=query, anio=anio), many=True)
                    establecimiento = {"results": establecimiento.data}
                    return JsonResponse(establecimiento, safe=False)
                else:
                    establecimiento = EstablecimientoSerializerShort(Establecimiento.objects.filter(anio=anio),
                                                                     many=True)
                    return JsonResponse(JSONH.pack(establecimiento.data), safe=False)
        else:
            if codigo_establecimiento:
                establecimiento = EstablecimientoSerializer(
                    Establecimiento.objects.get(codigo_establecimiento=codigo_establecimiento, anio=anio))
            else:
                establecimiento = EstablecimientoSerializer(Establecimiento.objects.filter(anio=anio), many=True)
        return JsonResponse(establecimiento.data, safe=False)


class InstitucionController(View):
    def get(self, request, *args, **kwargs):
        codigo_establecimiento = kwargs.get('codigo_establecimiento')
        query = request.GET.get('q')
        periodo = request.GET.get('periodo')
        offset = request.GET.get('offset')
        cantidad = request.GET.get('cantidad')
        tipos = ['nombre', 'codigo', 'direccion', 'distrito', 'barrio']
        tipo = request.GET.get('tipo')
        if tipo not in tipos:
            tipo = None
        if not periodo:
            periodo = '2014'
        if codigo_establecimiento:
            institucion = InstitucionSerializer(
                Institucion.objects.filter(codigo_establecimiento=codigo_establecimiento, periodo=periodo), many=True)
        else:
            if query is not None:
                instituciones = {
                    "results": {},
                    "query": query,
                    "tipo": tipo,
                    "periodo": periodo,
                    "base_url": reverse('index')
                }
                base_query = 'SELECT * FROM openfonacide_institucion inst ' \
                             'JOIN openfonacide_establecimiento est on ' \
                             '(est.anio=inst.periodo AND est.codigo_establecimiento=inst.codigo_establecimiento)'
                cursor = connection.cursor()
                if tipo is None or tipo == 'codigo':
                    cursor.execute(
                        base_query +
                        " WHERE inst.codigo_institucion = '" + escapelike(
                            query.upper()) + "' AND inst.periodo=%s order by inst.codigo_institucion",
                        [periodo]
                    )
                    institucion0 = dictfetch(cursor, cantidad, offset)
                    instituciones['results']["codigo"] = {
                        "name": "Codigo de Instituci&oacute;n",
                        "results": institucion0
                    }

                if tipo is None or tipo == 'nombre':
                    cursor.execute(
                        base_query +
                        " WHERE inst.nombre_institucion like '%%" + escapelike(
                            query.upper()) + "%%' AND inst.periodo=%s",
                        [periodo]
                    )
                    institucion1 = dictfetch(cursor, cantidad, offset)
                    instituciones['results']["nombre"] = {
                        "name": "Nombre",
                        "results": institucion1
                    }

                if tipo is None or tipo == 'direccion':
                    cursor.execute(
                        base_query +
                        " WHERE est.direccion like '%%" + escapelike(query.upper()) + "%%' AND inst.periodo=%s",
                        [periodo]
                    )
                    institucion2 = dictfetch(cursor, cantidad, offset)
                    instituciones['results']["direccion"] = {
                        "name": "Direccion",
                        "results": institucion2
                    }

                if tipo is None or tipo == 'distrito':
                    cursor.execute(
                        base_query +
                        " WHERE inst.nombre_distrito like '%%" + escapelike(query.upper()) + "%%' AND inst.periodo=%s",
                        [periodo]
                    )
                    institucion3 = dictfetch(cursor, cantidad, offset)
                    instituciones['results']["distrito"] = {
                        "name": "Distrito",
                        "results": institucion3
                    }

                if tipo is None or tipo == 'barrio':
                    cursor.execute(
                        base_query +
                        " WHERE inst.nombre_barrio_localidad like '%%" + escapelike(
                            query.upper()) + "%%' AND inst.periodo=%s",
                        [periodo]
                    )
                    institucion4 = dictfetch(cursor, cantidad, offset)
                    instituciones['results']["barrio"] = {
                        "name": "Barrio/Localidad",
                        "results": institucion4
                    }
                return JsonResponse(instituciones, safe=False)
            else:
                institucion = InstitucionSerializer(Institucion.objects.all(), many=True)
        return JsonResponse(institucion.data, safe=False)


class PrioridadController(View):
    def get(self, request, *args, **kwargs):
        codigo_establecimiento = kwargs.get('codigo_establecimiento')
        result = {
            "aulas": get_Pr(codigo_establecimiento, Espacio, EspacioSerializer).data,
            "sanitarios": get_Pr(codigo_establecimiento, Sanitario,
                                 SanitarioSerializer).data,
            "mobiliarios": get_Pr(codigo_establecimiento, Mobiliario,
                                  MobiliarioSerializer).data,
            "estados": get_Pr(codigo_establecimiento, ServicioBasico,
                              ServicioBasicoSerializer).data,

        }
        return JsonResponse(result, safe=False)


@login_required()
@transaction.atomic
def estado_de_obra(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido.'}, status=405)

    estado = request.POST.get('estado')
    clase_prioridad = request.POST.get('clase_prioridad')
    codigo_prioridad = request.POST.get('codigo_prioridad')
    verificado = request.POST.get('verificado')

    permisos = request.user.get_all_permissions()
    permiso_verificar = 'openfonacide.verificar_estado' in permisos
    permiso_cambiar = 'openfonacide.cambiar_estado' in permisos

    if not permiso_cambiar and not permiso_verificar:
        return JsonResponse({'error': 'No tiene permisos para realizar esta accion'}, status=403)

    if not estado or not clase_prioridad or not codigo_prioridad:
        return JsonResponse({'error': 'Datos insuficientes'}, status=400)

    documento = request.FILES.get('archivo')

    prioridad = None

    if clase_prioridad == 'Aulas' or clase_prioridad == 'Otros Espacios':
        prioridad = Espacio.objects.get(id=codigo_prioridad)
    if clase_prioridad == 'Mobiliarios':
        prioridad = Mobiliario.objects.get(id=codigo_prioridad)
    if clase_prioridad == 'Sanitarios':
        prioridad = Sanitario.objects.get(id=codigo_prioridad)

    if prioridad is None:
        return JsonResponse({'error': 'No existe prioridad.'}, status=404)

    current_user = request.user

    fecha_actual = datetime.now()

    # Si se realizo un cambio de estado
    cambio_estado = prioridad.estado_de_obra != estado

    cambio_verificacion = verificado is not None

    if cambio_estado and permiso_cambiar:
        fecha_modificacion = fecha_actual
        cambiado_por = current_user
    else:
        fecha_modificacion = prioridad.fecha_modificacion
        cambiado_por = prioridad.cambiado_por
        estado = prioridad.estado_de_obra

    if cambio_verificacion and permiso_verificar:
        fecha_verificacion = fecha_actual
        verificado_por = current_user
    else:
        fecha_verificacion = prioridad.fecha_verificacion
        verificado_por = prioridad.verificado_por

    if verificado_por and permiso_verificar and not cambio_estado:
        verificado_por_id = verificado_por.id
        verificado_por_email = verificado_por.email
    else:
        verificado_por_id = None
        verificado_por_email = None
        fecha_verificacion = None
        verificado_por = None

    if cambiado_por and permiso_verificar:
        cambiado_por_id = cambiado_por.id
        cambiado_por_email = cambiado_por.email
    else:
        cambiado_por_id = None
        cambiado_por_email = None

    historial = HistorialEstado(prioridad=codigo_prioridad, clase=clase_prioridad, fecha=fecha_actual,
                                estado_de_obra=estado, fecha_modificacion=fecha_modificacion,
                                cambiado_por_id=cambiado_por_id, cambiado_por_email=cambiado_por_email,
                                verificado_por_id=verificado_por_id, verificado_por_email=verificado_por_email,
                                documento=documento)
    historial.save()

    if historial.documento:
        documento_url = historial.documento.url
    else:
        documento_url = prioridad.documento

    prioridad.estado_de_obra = estado
    prioridad.fecha_modificacion = fecha_modificacion
    prioridad.cambiado_por = cambiado_por
    prioridad.fecha_verificacion = fecha_verificacion
    prioridad.verificado_por = verificado_por
    prioridad.documento = documento_url
    prioridad.save()

    return JsonResponse('Exito!', safe=False, status=200)


def reportar(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido.'}, status=405)
    form = ReporteForm(request.POST)
    if form.is_valid():
        reporte = form.save(commit=False)
        reporte.fecha = datetime.now()
        reporte.save()

        notificaciones = NotificacionesReportes.objects.all()

        emails = map(lambda obj: obj.email, notificaciones)

        if emails is not None and len(emails) > 0:

            institucion = Institucion.objects.filter(codigo_institucion=reporte.codigo_institucion)[:1].get()
            establecimiento = Establecimiento.objects.filter(codigo_establecimiento=institucion.codigo_establecimiento)[
                              :1].get()

            if reporte.tipo == 'aulas' or reporte.tipo == 'otros':
                prioridad = Espacio.objects.get(id=reporte.id_prioridad)
            elif reporte.tipo == 'mobiliarios':
                prioridad = Mobiliario.objects.get(id=reporte.id_prioridad)

            elif reporte.tipo == 'sanitarios':
                prioridad = Sanitario.objects.get(id=reporte.id_prioridad)
            else:
                prioridad = None

            ctx = {
                "tipo": reporte.tipo,
                "reporte": reporte,
                "institucion": institucion,
                "establecimiento": establecimiento,
                "prioridad": prioridad,
                "base_url": request.build_absolute_uri(reverse('index'))[:-1],
                "url_view_action": (request.build_absolute_uri(reverse('index')) + 'map/?establecimiento=' +
                                    reporte.codigo_establecimiento + '&institucion=' + reporte.codigo_institucion)
            }
            mensaje = get_template('registration/mail.nuevoreporte.html').render(Context(ctx))
            to = emails
            mail = EmailMultiAlternatives(
                settings.EMAIL_SUBJECT_PREFIX + 'Reporte institucion: ' + reporte.codigo_institucion,
                mensaje,
                bcc=to,
                from_email=settings.EMAIL_HOST_USER)
            mail.attach_alternative(mensaje, "text/html")
            mail.send()

        return JsonResponse({'mensaje': 'Exito.'}, status=200)
    return JsonResponse({'error': 'Datos inválidos'}, status=400)


@login_required()
@transaction.atomic
def agregar_adjudicacion(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Método inválido.'}, status=405)

    codigo_institucion = request.POST.get('codigo_institucion')
    id_llamado = request.POST.get('id_llamado')
    periodo = request.POST.get('periodo')

    permisos = request.user.get_all_permissions()
    permiso_verificar = 'openfonacide.verificar_estado' in permisos
    permiso_cambiar = 'openfonacide.cambiar_estado' in permisos

    if not permiso_cambiar and not permiso_verificar:
        return JsonResponse({'error': 'No tiene permisos para realizar esta accion'}, status=403)

    if not id_llamado or not codigo_institucion or not periodo:
        return JsonResponse({'error': 'Datos insuficientes'}, status=400)

    try:
        i = Institucion.objects.get(codigo_institucion=codigo_institucion, periodo=periodo)
    except ObjectDoesNotExist:
        return JsonResponse({'error': 'No existe la institución'}, status=400)

    a = None
    try:
        p = Planificacion.objects.get(id_llamado=id_llamado, anio=periodo)
        a = Adjudicacion.objects.get(id_llamado=id_llamado)
    except ObjectDoesNotExist:
        pass

    i.planificaciones.add(p)
    if a is not None:
        i.adjudicaciones.add(a)

    try:
        Temporal.objects.get(codigo_institucion=codigo_institucion, periodo=periodo, id_llamado=id_llamado).delete()
    except:
        pass

    return JsonResponse({'mensaje': 'Éxito'}, status=200)
