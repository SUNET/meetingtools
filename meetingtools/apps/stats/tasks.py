import logging
from celery.schedules import crontab
from celery.task import periodic_task
from meetingtools.ac import ac_api_client
from meetingtools.apps.cluster.models import ACCluster
from datetime import datetime,timedelta
from meetingtools.apps.stats.models import UserMeetingTransaction

__author__ = 'leifj'

def import_acc_sessions(acc,since=0):
    with ac_api_client(acc) as api:
        p = {'sort': 'asc','sort1': 'date-created','filter-type': 'meeting'}

        begin = None
        if since > 0:
            begin = datetime.now()-timedelta(seconds=since)
            begin = begin.replace(microsecond=0)

        if begin is not None:
            p['filter-gte-date-created'] = begin.isoformat()

        r = api.request('report-bulk-consolidated-transactions',p,True)
        for tx in r.et.findall(".//row"):
            try:
                UserMeetingTransaction.create(acc,tx)
            except Exception,ex:
                logging.error(ex)

@periodic_task(run_every=crontab(hour="*", minute="*", day_of_week="*"))
def import_sessions(since=3700):
    for acc in ACCluster.objects.all():
        import_acc_sessions(acc,since)