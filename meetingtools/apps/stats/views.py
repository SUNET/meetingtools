"""
Created on Jan 16, 2012

@author: leifj
"""
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import naturalday
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from meetingtools.apps.stats.models import UserMeetingTransaction
from iso8601 import iso8601
from time import mktime
from meetingtools.multiresponse import json_response, respond_to
from meetingtools.apps.stats.forms import StatCaledarForm
from django.shortcuts import get_object_or_404
from meetingtools.apps.room.models import Room

def _iso2datesimple(iso):
    (date,rest) = iso.split("T")
    return date

def _dt2ts(dt):
    return mktime(dt.timetuple())*1000

def _iso2ts(iso):
    return mktime(iso8601.parse_date(iso).timetuple())*1000

def _iso2dt(iso):
    return iso8601.parse_date(iso)

def _date_ts(date):
    (y,m,d) = date.split("-")
    return int(mktime((int(y),int(m),int(d),0,0,0,0,0,-1)))*1000 # midnight

@login_required
def user(request,username=None):
    if username is None:
        username = request.user.username
    (local,domain) = username.split('@')
    return respond_to(request,{'text/html': 'apps/stats/user.html'},{'domain': domain,'username': username})

@login_required
def domain(request,domain):
    (l,d) = request.user.username.split('@')
    if d != domain:
        return HttpResponseForbidden("You can only look at statistics for your own domain!")
    
    return respond_to(request,{'text/html': 'apps/stats/domain.html'},{'domain': domain})

@login_required
def room(request,rid):
    room = get_object_or_404(Room,pk=rid)
    if not room.creator == request.user:
        return HttpResponseForbidden("You can only look at statistics for your own rooms!")
    
    return respond_to(request,{'text/html': 'apps/stats/room.html'},{'room': room})

@login_required
def tagged_minutes_api(request):
    form = StatCaledarForm(request.GET) # convenient way to parse dates
    if not form.is_valid():
        return HttpResponseBadRequest()

    tags = filter(lambda x: bool(x), form.cleaned_data['tags'].strip().split("+"))
    sco = form.cleaned_data['sco']
    begin = form.cleaned_data['begin']
    end = form.cleaned_data['end']
    user = form.cleaned_data['user']

    qs = UserMeetingTransaction.objects

    if user:
        qs = qs.filter(user=user)
    if sco:
        qs = qs.filter(sco=sco)
    if begin:
        qs = qs.filter(date_created__gt=begin)
    if end:
        qs = qs.filter(date_closed__lt=end)

    if len(tags) > 0:
        qs = UserMeetingTransaction.tagged.with_all(tags,qs)

    series = []
    d_created  = None
    d_closed = None
    ms = 0
    curdate = None
    t_ms = 0
    rc = {}
    uc = {}

    for tx in qs.all().prefetch_related("sco").prefetch_related("user"):
        rc[tx.sco.id] = True
        uc[tx.user.username] = True
        ts_created = _dt2ts(tx.date_created)
        ts_closed = _dt2ts(tx.date_closed)

        d1 = tx.date_created
        if d_created is None:
            d_created = d1

        d2 = tx.date_closed
        if d_closed is None:
            d_closed = d2

        if curdate is None:
            curdate = d1

        if curdate != d1:
            series.append([_dt2ts(curdate),int(ms/60)])
            ms = 0
            curdate = d1

        if d1 == d2: #same date
            diff = (ts_closed - ts_created)
            ms += diff
            t_ms += diff
        else: # meeting spanned midnight
            ts_date_ts = _dt2ts(d2)
            ms += ts_date_ts - ts_created
            series.append([_dt2ts(d1),int(ms/60)])
            t_ms += ms
            curdate = d2
            ms = (ts_closed - ts_date_ts)

    if curdate is not None and ms > 0:
        series.append([_date_ts(curdate),int(ms/60)])

    return json_response({'data': sorted(series,key=lambda x: x[0]),
                          'rooms': len(rc.keys()),
                          'begin': naturalday(begin),
                          'end': naturalday(end),
                          'users': len(uc.keys()),
                          'minutes': int(t_ms/60)},request)
