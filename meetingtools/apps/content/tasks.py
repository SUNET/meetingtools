# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from meetingtools.ac import ac_api_client
from meetingtools.apps.content.models import Content
import logging
from datetime import datetime, timedelta
from celery.task import periodic_task
from celery.schedules import crontab
from meetingtools.apps.cluster.models import ACCluster


def import_acc(acc, since=0):
    with ac_api_client(acc) as api:
        if since > 0:
            then = datetime.now()-timedelta(seconds=since)
            then = then.replace(microsecond=0)
            r = api.request('report-bulk-objects',
                            {'filter-out-type': 'meeting', 'filter-gt-date-modified': then.isoformat()})
        else:
            r = api.request('report-bulk-objects', {'filter-out-type': 'meeting'})
        if r:
            nr = 0
            for row in r.et.xpath("//row"):
                Content.create(acc, api, row)
                nr += 1
            logging.info("%s: Imported %d objects." % (acc, nr))


@periodic_task(run_every=crontab(hour="*", minute="*/15", day_of_week="*"))
def import_all_content():
    for acc in ACCluster.objects.all():
        import_acc(acc, since=960)


#@periodic_task(run_every=crontab(hour="1", minute="0", day_of_week="*"))
def timed_full_import():
    for acc in ACCluster.objects.all():
        import_acc(acc)