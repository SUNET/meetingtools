from __future__ import absolute_import
# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import os
from celery import Celery
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meetingtools.settings')

app = Celery('meetingtools', broker='amqp://guest@localhost//',)

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

# Optional configuration, see the application user guide.
app.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
    CELERY_TIMEZONE='Europe/Stockholm',
    CELERY_ENABLE_UTC=True
)

if __name__ == '__main__':
    app.start()