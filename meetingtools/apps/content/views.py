# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponseForbidden
from django.core.cache import cache
from meetingtools.multiresponse import respond_to
from django.shortcuts import get_object_or_404
from tagging.models import Tag
from meetingtools.apps.content.models import Content
from meetingtools.apps.cluster.models import ACCluster
from meetingtools.apps.content import tasks


@login_required
def user(request, username=None):
    if username is None:
        username = request.user.username
    content = cache.get('%s-content' % username)
    total_bytecount = cache.get('%s-bytecount' % username)
    if not content or total_bytecount:
        content = Content.objects.filter(creator__username=username)
        total_bytecount = content.aggregate(Sum('bytecount'))
        cache.set('%s-content' % username, content, 900)
        cache.set('%s-bytecount' % username, total_bytecount, 900)
    return respond_to(request, {'text/html': 'apps/content/user.html'},
                      {'username': username, 'content': content, 'total_bytecount': total_bytecount})


@login_required
def cluster(request, cluster_name=None):

    if not request.user.is_staff:
        return HttpResponseForbidden()

    clusters = ACCluster.objects.all().values('name')
    if cluster_name:
        acc = get_object_or_404(ACCluster, name=cluster_name)
        domains = cache.get('%s-domains' % acc)
        total_bytecount = cache.get('%s-bytecount' % acc)
        if not domains or not total_bytecount:
            domains, total_bytecount = tasks.get_cluster_content(acc)

        return respond_to(request, {'text/html': 'apps/content/cluster.html'},
                          {'clusters': clusters, 'cluster_name': cluster_name, 'domains': domains,
                           'total_bytecount': total_bytecount})

    return respond_to(request, {'text/html': 'apps/content/cluster.html'},
                      {'clusters': clusters})


@login_required
def domain(request, domain_name):

    if not request.user.is_staff:
        return HttpResponseForbidden()

    domain_tag = get_object_or_404(Tag, name='domain:%s' % domain_name)
    users = cache.get('%s-users' % domain_tag)
    total_files = cache.get('%s-files' % domain_tag)
    total_bytecount = cache.get('%s-bytecount' % domain_tag)
    if not users or not total_files or not total_bytecount:
        users, total_files, total_bytecount = tasks.get_domain_content(domain_tag)

    return respond_to(request, {'text/html': 'apps/content/domain.html'},
                      {'domain': domain_name, 'total_bytecount': total_bytecount, 'total_files': total_files,
                       'users': users})
