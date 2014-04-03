# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from meetingtools.ac import ac_api_client
from meetingtools.ac.api import ACPException
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
    years = [2009, 2010, 2011, 2012, 2013, 2014]
    for acc in ACCluster.objects.all():
        nr = 0
        for year in years:
            begin = datetime(year=year, month=1, day=1)
            end = datetime(year=year, month=12, day=31)
            with ac_api_client(acc) as api:
                try:
                    r = api.request('report-bulk-objects',
                                    {'filter-out-type': 'meeting',
                                     'filter-gte-date-modified': begin.isoformat(),
                                     'filter-lte-date-modified': end.isoformat()},
                                    raise_error=True)
                    if r:
                        nr = 0
                        for row in r.et.xpath("//row"):
                            Content.create(acc, api, row)
                            nr += 1
                except ACPException as e:
                    logging.error('ACPException in content.timed_full_import')
                    logging.error(e)
                    pass
                except Exception as e:
                    logging.error('Exception in content.timed_full_import')
                    logging.error(e)
                    pass
                logging.info("%s: Imported %d objects." % (acc, nr))