import json
from django.db import connection
from django.http import JsonResponse


# Genera JSON de ubicaciones
#
def generar_ubicacion(request):
    cursor = connection.cursor()
    query = ('SELECT codigo_departamento, min(nombre_departamento), codigo_distrito,'
            'min(nombre_distrito), codigo_barrio_localidad, min(nombre_barrio_localidad) '
            'FROM openfonacide_establecimiento '
            'WHERE nombre_barrio_localidad NOT LIKE \'%CONFIRMAR%\' '
            'GROUP BY codigo_departamento, codigo_distrito, codigo_barrio_localidad '
            'ORDER BY codigo_departamento, codigo_distrito, codigo_barrio_localidad')
    cursor.execute(query)
    rows = cursor.fetchall()
    # [dep, dis, bar ]
    anterior = [None, None, None]
    actual = [None, None, None]
    dep = None
    dis = None
    bar = None
    result = []
    for row in rows:
        actual[0] = row[0]
        actual[1] = row[2]
        actual[2] = row[4]

        if anterior[0] != actual[0]:
            dep = {'id': row[0], 'nombre': row[1], 'distritos':[]}
            result.append(dep)

        if anterior[1] != actual[1]:
            dis = {'id': row[2], 'nombre': row[3], 'barrios':[]}
            dep.get('distritos').append(dis)

        if anterior[2] != actual[2]:
            bar = {'id': row[4], 'nombre': row[5]}
            dis.get('barrios').append(bar)

        anterior[0] = row[0]
        anterior[1] = row[2]
        anterior[2] = row[4]
    cursor.close()
    return JsonResponse(result, safe=False)

def filtros(request):
    prioridades = request.GET.get('prioridades')

    ubicacion = request.GET.get('ubicacion')
    reportadas = request.GET.get('reportadas')
    if reportadas == 'true':
        reportadas = True
    else:
        reportadas = None
    documentos = request.GET.get('documentos')
    if documentos == 'true':
        documentos = True
    else:
        documentos = None
    # adjudicaciones = request.GET.get('adjudicaciones')
    # planificaciones = request.GET.get('planificaciones')
    estado = request.GET.get('estado')
    if reportadas or documentos or estado and estado.lower() in ('priorizado', 'planificado', 'adjudicado', 'terminado'):
        if not prioridades:
            prioridades = json.dumps({'mobiliarios': True, 'sanitarios': True, 'aulas': True, 'otros': True})
    if prioridades:
        prioridades = json.loads(prioridades)
        tipo = []
        rango = get_rango(prioridades.get('rango'))
        if ubicacion:
            ubicacion = json.loads(ubicacion)
        else:
            ubicacion = {}
        for key in prioridades:
            if prioridades.get(key):
                tipo.append(key)
        return JsonResponse(filtro_prioridad(tipo, rango, ubicacion, estado, documentos, reportadas), safe=False)
    else:
        if ubicacion:
            ubicacion = json.loads(ubicacion)
        else:
            ubicacion = {}
        return JsonResponse(filtro_ubicacion(ubicacion), safe=False)

def get_rango(rango):

    if not rango or len(rango) != 2:
        return [0, 200]
    try:
        rango0 = int(float(rango[0]))
        rango1 = int(float(rango[1]))
        if rango0 > rango1:
            rango0, rango1 = rango1, rango0
        if rango0 == rango1:
            rango0 = 0
            rango1 = 200
        if rango0 >= 200 or rango1 > 200:
            rango0 = 0
            rango1 = 200
    except ValueError:
        rango0 = 0
        rango1 = 200
    ret = [rango0, rango1]
    return ret


def filtro_prioridad(tipo, rango, ubicacion, estado, documentos, reportadas):
    cursor = connection.cursor()
    cursor.execute(query_prioridad(tipo, rango, ubicacion, estado, documentos, reportadas))
    rows = cursor.fetchall()
    rows = map(lambda x: x[0], rows)
    cursor.close()
    if rows == {}:
        return []
    return rows


def query_prioridad(tipo, rango, ubicacion, estado, documentos, reportadas):
    begin_query = ('SELECT DISTINCT codigo_establecimiento FROM (')
    union = False

    query_estado = ''
    if estado and estado.lower() in ('priorizado', 'planificado', 'adjudicado', 'terminado'):
        query_estado = " AND lower(estado_de_obra) = '%s' " % estado

    query_reportadas = ''
    if reportadas:
        query_reportadas = " JOIN openfonacide_reportes re ON re.id_prioridad = %s.id AND re.tipo = '%s' "

    query_documentos = ''
    if documentos:
        query_documentos = ' AND documento IS NOT NULL '

    query_ubicacion = ''
    dep_id = ubicacion.get('departamento')
    if dep_id:
        query_ubicacion += ' AND '
        query_ubicacion += ' es.codigo_departamento = \'' + dep_id + '\' '

    dis_id = ubicacion.get('distrito')
    if dis_id:
        query_ubicacion += ' AND '
        query_ubicacion += ' es.codigo_distrito = \'' + dis_id + '\' '

    bar_id = ubicacion.get('barrio')
    if bar_id:
        query_ubicacion += ' AND '
        query_ubicacion += ' es.codigo_barrio_localidad = \'' + bar_id + '\' '

    if tipo == 'mobiliarios' or 'mobiliarios' in tipo:
        begin_query += ('SELECT p_mob.codigo_establecimiento '
                'FROM openfonacide_mobiliario p_mob '
                'JOIN openfonacide_establecimiento es '
                'ON es.codigo_establecimiento = p_mob.codigo_establecimiento ')
        if reportadas:
            begin_query += query_reportadas % ('p_mob', 'mobiliarios')
        begin_query += ('WHERE p_mob.numero_prioridad >= '+ str(rango[0]) +
                ' AND p_mob.numero_prioridad <= ' + str(rango[1]))
        begin_query += query_documentos
        begin_query += query_estado
        begin_query += query_ubicacion
        union = True
    if tipo == 'sanitarios' or 'sanitarios' in tipo:
        if union:
            begin_query += 'UNION '
        begin_query += ('SELECT p_san.codigo_establecimiento '
                'FROM openfonacide_sanitario p_san '
                'JOIN openfonacide_establecimiento es '
                'ON es.codigo_establecimiento = p_san.codigo_establecimiento ')
        if reportadas:
            begin_query += query_reportadas % ('p_san', 'sanitarios')
        begin_query += ('WHERE p_san.numero_prioridad >= '+ str(rango[0]) +
                ' AND p_san.numero_prioridad <= ' + str(rango[1]))
        begin_query += query_documentos
        begin_query += query_estado
        begin_query += query_ubicacion
        union = True
    if tipo == 'aulas' or 'aulas' in tipo:
        if union:
            begin_query += 'UNION '
        begin_query += ('SELECT p_au.codigo_establecimiento '
                'FROM openfonacide_espacio p_au '
                'JOIN openfonacide_establecimiento es '
                'ON es.codigo_establecimiento = p_au.codigo_establecimiento ')
        if reportadas:
            begin_query += query_reportadas % ('p_au', 'aulas')
        begin_query += (' where p_au.nombre_espacio is null '
                ' and p_au.numero_prioridad >= ' + str(rango[0]) +
                ' and p_au.numero_prioridad <= ' + str(rango[1]))
        begin_query += query_documentos
        begin_query += query_estado
        begin_query += query_ubicacion
        union = True
    if tipo == 'otros' or 'otros' in tipo:
        if union:
            begin_query += 'UNION '
        begin_query += ('SELECT p_es.codigo_establecimiento '
                'FROM openfonacide_espacio p_es '
                'JOIN openfonacide_establecimiento es '
                'ON es.codigo_establecimiento = p_es.codigo_establecimiento ')
        if reportadas:
            begin_query += query_reportadas % ('p_es', 'otros')
        begin_query += (' where p_es.nombre_espacio is not null '
                ' and p_es.numero_prioridad >= ' + str(rango[0]) +
                ' and p_es.numero_prioridad <= ' + str(rango[1]))
        begin_query += query_documentos
        begin_query += query_estado
        begin_query += query_ubicacion
        union = True
    begin_query += ") other "
    if not union:
        return "SELECT 1 WHERE 1 = 0"
    return begin_query

def filtro_ubicacion(ubicacion):
    query_ubicacion = ''
    dep_id = ubicacion.get('departamento')
    if dep_id:
        query_ubicacion += ' where '
        query_ubicacion += ' es.codigo_departamento = \'' + dep_id + '\' '

    dis_id = ubicacion.get('distrito')
    if dis_id:
        query_ubicacion += ' and '
        query_ubicacion += ' es.codigo_distrito = \'' + dis_id + '\' '

    bar_id = ubicacion.get('barrio')
    if bar_id:
        query_ubicacion += ' and '
        query_ubicacion += ' es.codigo_barrio_localidad = \'' + bar_id + '\' '

    if query_ubicacion == '':
        return []

    query = ('SELECT DISTINCT codigo_establecimiento '
             'FROM openfonacide_establecimiento es ')
    query += query_ubicacion
    cursor = connection.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    rows = map(lambda x: x[0], rows)
    cursor.close()
    if rows == {}:
        return []
    return rows
