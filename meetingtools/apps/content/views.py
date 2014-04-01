# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.contrib.humanize.templatetags.humanize import naturalday
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from meetingtools.apps.stats.models import UserMeetingTransaction
from iso8601 import iso8601
from time import mktime
from meetingtools.multiresponse import json_response, respond_to
from meetingtools.apps.stats.forms import StatCaledarForm
from django.shortcuts import get_object_or_404
from meetingtools.apps.content.models import Content


@login_required
def user(request, username=None):
    if username is None:
        username = request.user.username
    content = Content.objects.filter(creator__username=username)
    total_bytecount = content.aggregate(Sum('bytecount'))
    return respond_to(request,{'text/html': 'apps/content/user.html'},
                      {'username': username, 'content': content, 'total_bytecount': total_bytecount})