# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Sum, Count
from django.contrib.auth.models import User
from django.contrib.humanize.templatetags.humanize import naturalday
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from meetingtools.apps.stats.models import UserMeetingTransaction
from iso8601 import iso8601
from time import mktime
from meetingtools.multiresponse import json_response, respond_to
from meetingtools.apps.stats.forms import StatCaledarForm
from django.shortcuts import get_object_or_404
from tagging.models import Tag, TaggedItem
from meetingtools.apps.content.models import Content
from meetingtools.apps.cluster.models import ACCluster


@login_required
def user(request, username=None):
    if username is None:
        username = request.user.username
    content = Content.objects.filter(creator__username=username)
    total_bytecount = content.aggregate(Sum('bytecount'))
    return respond_to(request,{'text/html': 'apps/content/user.html'},
                      {'username': username, 'content': content, 'total_bytecount': total_bytecount})


@login_required
def cluster(request, cluster_name=None):

    if not request.user.is_staff:
        return HttpResponseForbidden

    clusters = ACCluster.objects.all().values('name')
    if cluster_name:
        total_bytecount = 0
        domains = []
        acc = get_object_or_404(ACCluster, name=cluster_name)
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
        return respond_to(request, {'text/html': 'apps/content/cluster.html'},
                          {'clusters': clusters, 'cluster_name': cluster_name, 'domains': domains,
                           'total_bytecount': total_bytecount})

    return respond_to(request, {'text/html': 'apps/content/cluster.html'},
                      {'clusters': clusters})


@login_required
def domain(request, domain_name):

    if not request.user.is_staff:
        return HttpResponseForbidden

    users = []
    tag = get_object_or_404(Tag, name='domain:%s' % domain_name)
    qs = TaggedItem.objects.get_by_model(Content, tag)
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
    return respond_to(request, {'text/html': 'apps/content/domain.html'},
                      {'domain': domain_name, 'total_bytecount': total_bytecount, 'total_files': total_files,
                       'users': users})
