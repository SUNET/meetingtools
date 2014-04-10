# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from meetingtools.ac import ac_api_client
from meetingtools.ac.api import ACPException
from meetingtools.apps.content.models import Content
from meetingtools.apps.cluster.models import ACCluster
from celery.task import periodic_task
from celery.schedules import crontab
from tagging.models import Tag, TaggedItem
from datetime import datetime, timedelta
import logging


@periodic_task(run_every=crontab(hour="*", minute="*/10", day_of_week="*"))
def import_all_content():
    for acc in ACCluster.objects.all():
        import_acc(acc, since=900)


@periodic_task(run_every=crontab(hour="*", minute="*/15", day_of_week="*"))
def cache_cluster_content():
    for acc in ACCluster.objects.all():
        get_cluster_content(acc)


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
            logging.info("%s: Imported %d content objects." % (acc, nr))


def get_cluster_content(acc):
    total_bytecount = 0
    domains = []
    tags = Tag.objects.usage_for_model(Content, filters={'sco__acc': acc})
    for tag in sorted(tags):
        if tag.name.startswith('domain:'):
            qs = TaggedItem.objects.get_by_model(Content, tag)
            d = {
                'domain': tag.name.split('domain:')[1],
                'domain_bytes': qs.aggregate(Sum('bytecount'))['bytecount__sum'],
                'number_of_files': len(qs)
            }
            total_bytecount += d['domain_bytes']
            domains.append(d)
    cache.set('%s-domains' % acc, domains, 900)
    cache.set('%s-bytecount' % acc, total_bytecount, 900)
    return domains, total_bytecount


def get_domain_content(domain_tag):
    users = []
    qs = TaggedItem.objects.get_by_model(Content, domain_tag)
    total_files = len(qs)
    total_bytecount = qs.aggregate(Sum('bytecount'))['bytecount__sum']
    creators = qs.values('creator').annotate(num_files=Count('creator'))
    for creator in creators:
        domain_user = get_object_or_404(User, pk=creator['creator'])
        d = {
            'username': domain_user.username,
            'number_of_files': creator['num_files'],
            'bytecount': Content.objects.filter(creator=domain_user).aggregate(Sum('bytecount'))['bytecount__sum']
        }
        users.append(d)
    cache.set('%s-users' % domain_tag, users, 900)
    cache.set('%s-files' % domain_tag, total_files, 900)
    cache.set('%s-bytecount' % domain_tag, total_bytecount, 900)
    return users, total_files, total_bytecount


#@periodic_task(run_every=crontab(hour="1", minute="0", day_of_week="*"))
def timed_full_import():
    years = [2009, 2010, 2011, 2012, 2013, 2014]
    months = [(1, 7), (8, 12)]  # Ugly hack as June does not have 31 days
    for acc in ACCluster.objects.all():
        nr = 0
        for year in years:
            for month in months:
                begin = datetime(year=year, month=month[0], day=1)
                end = datetime(year=year, month=month[1], day=31)
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
                        logging.error('Period %s %s-%s failed for cluster %s.' % (year, month[0], month[1], acc))
                        logging.error(e)
                        pass
                    except Exception as e:
                        logging.error('Exception in content.timed_full_import')
                        logging.error(e)
                        pass
                    logging.info("%s: Imported %d content objects." % (acc, nr))