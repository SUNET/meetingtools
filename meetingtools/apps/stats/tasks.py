import logging
from celery.schedules import crontab
from celery.task import periodic_task, task
from meetingtools.apps.room.models import Room
from meetingtools.ac import ac_api_client
from meetingtools.apps.cluster.models import ACCluster
from datetime import datetime,timedelta
from meetingtools.apps.stats.models import UserMeetingTransaction

__author__ = 'leifj'


def import_acc_sessions(acc,since=0,room_last_visited=False):
    with ac_api_client(acc) as api:
        p = {'sort': 'asc','sort1': 'date-created','filter-type': 'meeting'}

        begin = None
        if since > 0:
            begin = datetime.now()-timedelta(seconds=since)
            begin = begin.replace(microsecond=0)

        if begin is not None:
            p['filter-gte-date-created'] = begin.isoformat()

        r = api.request('report-bulk-consolidated-transactions',p,True)
        nr = 0
        ne = 0
        for tx in r.et.findall(".//row"):
            try:
                tx = UserMeetingTransaction.create(acc,tx)
                if tx:
                    if room_last_visited:
                        rooms = Room.objects.filter(sco=tx.sco)
                        if len(rooms) == 1:
                            room = rooms[0]
                            if room.lastvisited is None or room.lastvisited < tx.date_closed:
                                room.lastvisited = tx.date_created
                                room.save()
                    nr += 1
            except Exception,ex:
                logging.error(ex)
                ne += 1
        logging.info("%s: Imported %d transactions with %d errors" % (acc,nr,ne))

@task
def import_sessions(since,room_last_visited=False):
    for acc in ACCluster.objects.all():
        import_acc_sessions(acc,since,room_last_visited)

@periodic_task(run_every=crontab(hour="*", minute="*/5", day_of_week="*"))
def _hourly_import():
    import_sessions(600,True)


#@periodic_task(run_every=crontab(hour="5", minute="0", day_of_week="*"))
def timed_full_import():
    years = [2009, 2010, 2011, 2012, 2013, 2014]
    months = [(1, 3), (4, 7), (8, 10), (9, 12)]
    for acc in ACCluster.objects.all():
        for year in years:
            for month in months:
                begin = datetime(year=year, month=month[0], day=1)
                end = datetime(year=year, month=month[1], day=31)
                with ac_api_client(acc) as api:
                    p = {'sort': 'asc', 'sort1': 'date-created', 'filter-type': 'meeting',
                         'filter-gte-date-created': begin.isoformat(), 'filter-lte-date-created': end.isoformat()}
                    r = api.request('report-bulk-consolidated-transactions', p, False)
                    nr = 0
                    ne = 0
                    for tx in r.et.findall(".//row"):
                        try:
                            tx = UserMeetingTransaction.create(acc, tx)
                            if tx:
                                rooms = Room.objects.filter(sco=tx.sco)
                                if len(rooms) == 1:
                                    room = rooms[0]
                                    if room.lastvisited is None or room.lastvisited < tx.date_closed:
                                        room.lastvisited = tx.date_created
                                        room.save()
                                nr += 1
                        except Exception, ex:
                            logging.error(ex)
                            ne += 1
                    logging.info("%s: Imported %d transactions with %d errors" % (acc, nr, ne))