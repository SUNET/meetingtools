# Django settings for meetingtools project.

import meetingtools.site_logging
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

BASE_DIR = '.'

PREFIX_URL = ""
BASE_URL = "http://localhost:8000%s" % PREFIX_URL
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '%s/db/sqlite.db' % BASE_DIR,                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

GRACE = 10

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Stockholm'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

MEDIA_ROOT = "%s/site-media" % BASE_DIR
ADMIN_MEDIA_ROOT = "%s/admin-media" % BASE_DIR
MEDIA_URL = '%s/site-media/' % PREFIX_URL
ADMIN_MEDIA_PREFIX = '%s/admin-media/' % PREFIX_URL


LOGIN_URL = "%s/accounts/login/" % PREFIX_URL
LOGOUT_URL = "%s/accounts/logout/" % PREFIX_URL

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'tz78l!c=cl2=jic5$2#(bq)7-4s1ivtm*a+q0w1yi0$)hrmc7l'

SESSION_ENGINE = "django.contrib.sessions.backends.file"
SESSION_FILE_PATH = "/tmp"
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware'
)

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.RemoteUserBackend',
    'django.contrib.auth.backends.ModelBackend',
)

ROOT_URLCONF = 'meetingtools.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "%s/templates" % BASE_DIR
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django_extensions',
    'django_co_connector',
    'django_co_acls',
    'meetingtools.extensions',
    'meetingtools.apps.auth',
    'meetingtools.apps.room',
    'meetingtools.apps.cluster',
    'meetingtools.apps.userprofile',
)
