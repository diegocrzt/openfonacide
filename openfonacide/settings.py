# encoding: utf-8
# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import socket
import sys

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# openshift is our PAAS for now.
ON_PAAS = 'OPENSHIFT_REPO_DIR' in os.environ
ON_MEC = 'MEC_REPO_DIR' in os.environ


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

if ON_PAAS:
    SECRET_KEY = os.environ['OPENSHIFT_SECRET_TOKEN']
elif ON_MEC:
    SECRET_KEY = os.environ['MEC_SECRET_TOKEN']
else:
    SECRET_KEY = ')_7av^!cy(wfx=k#3*7x+(=j^fzv+ot^1@sh9s9t=8$bu@r(z$'

# SECURITY WARNING: don't run with debug turned on in production!
# adjust to turn off when on Openshift, but allow an environment variable to override on PAAS
DEBUG = not ON_PAAS
DEBUG = DEBUG or 'DEBUG' in os.environ
if ON_PAAS and DEBUG:
    print("*** Warning - Debug mode is on ***")

if ON_MEC:
    DEBUG = False

TEMPLATE_DEBUG = False

if ON_PAAS:
    ALLOWED_HOSTS = [os.environ['OPENSHIFT_APP_DNS'], socket.gethostname()]
elif ON_MEC:
    ALLOWED_HOSTS = [os.environ['MEC_APP_DNS'], socket.gethostname()]
else:
    ALLOWED_HOSTS = ['localhost']


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'import_export',
    'rest_framework',
    'rest_framework_swagger',
    'openfonacide'
)

SWAGGER_SETTINGS = {
    "exclude_namespaces": ["private_api"],
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '333/minute',
        'user': '500/minute'
    }

}

MIDDLEWARE_CLASSES = (
    # 'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'openfonacide.urls'

WSGI_APPLICATION = 'openfonacide.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

if ON_PAAS:
    # determine if we are on MySQL or POSTGRESQL
    if "OPENSHIFT_POSTGRESQL_DB_USERNAME" in os.environ:

        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': os.environ['OPENSHIFT_APP_NAME'],
                'USER': os.environ['OPENSHIFT_POSTGRESQL_DB_USERNAME'],
                'PASSWORD': os.environ['OPENSHIFT_POSTGRESQL_DB_PASSWORD'],
                'HOST': os.environ['OPENSHIFT_POSTGRESQL_DB_HOST'],
                'PORT': os.environ['OPENSHIFT_POSTGRESQL_DB_PORT'],
            }
        }

    elif "OPENSHIFT_MYSQL_DB_USERNAME" in os.environ:

        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': os.environ['OPENSHIFT_APP_NAME'],
                'USER': os.environ['OPENSHIFT_MYSQL_DB_USERNAME'],
                'PASSWORD': os.environ['OPENSHIFT_MYSQL_DB_PASSWORD'],
                'HOST': os.environ['OPENSHIFT_MYSQL_DB_HOST'],
                'PORT': os.environ['OPENSHIFT_MYSQL_DB_PORT'],
            }
        }


elif ON_MEC:
    # Postgres es obligatorio en el MEC
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': os.environ['MEC_APP_NAME'],
            'USER': os.environ['MEC_POSTGRESQL_DB_USERNAME'],
            'PASSWORD': os.environ['MEC_POSTGRESQL_DB_PASSWORD'],
            'HOST': os.environ['MEC_POSTGRESQL_DB_HOST'],
            'PORT': os.environ['MEC_POSTGRESQL_DB_PORT'],
        }
    }

else:
    # stock django
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql_psycopg2',
            'NAME': 'openfonacide',
            'USER': 'fonacide',
            'PASSWORD': '12345',
            'HOST': 'localhost',
            'PORT': '5432'
        }
    }
if "test" in sys.argv:
    DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'
    DATABASES['default']['NAME'] = 'sqlite3'

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'templates'),
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth'
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'wsgi', 'static')
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',

)

STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(BASE_DIR, "static"),
)

if ON_MEC:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_USE_TLS = True
    EMAIL_HOST = os.environ.get('MEC_EMAIL_HOST')
    EMAIL_PORT = os.environ.get('MEC_EMAIL_PORT')
    EMAIL_HOST_USER = os.environ.get('MEC_EMAIL_HOST_USER')
    EMAIL_HOST_PASSWORD = os.environ.get('MEC_EMAIL_HOST_PASSWORD')
    EMAIL_SUBJECT_PREFIX = '[ContralorFonacide] '
    EMAIL_USE_SSL = False
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    EMAIL_SUBJECT_PREFIX = '[ContralorFonacide] '
    EMAIL_HOST_USER = 'openfonacide@gmail.com'

if ON_PAAS:
    MEDIA_ROOT = os.path.join(os.environ.get('OPENSHIFT_DATA_DIR', ''), 'media')
else:
    MEDIA_ROOT = os.path.join(BASE_DIR, 'wsgi', 'files')

MEDIA_URL = '/media/'

# Ajustes especiales para el caso de un servidor detrás de un ReverseProxy
if ON_MEC:
    STATIC_URL = '/contralorfonacide/static/'
    MEDIA_URL = 'media/'
