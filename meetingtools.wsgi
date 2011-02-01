import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'meetingtools.settings'

sys.path.append('/var/www/meetingtools')
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
