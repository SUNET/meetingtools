'''
Created on Jan 16, 2012

@author: leifj
'''
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from meetingtools.ac import ac_api_client
from iso8601 import iso8601
from time import mktime
from meetingtools.multiresponse import json_response, respond_to
from meetingtools.apps.stats.forms import StatCaledarForm
from django.shortcuts import get_object_or_404
from meetingtools.apps.room.models import Room

def _iso2datesimple(iso):
    (date,rest) = iso.split("T")
    return date

def _iso2ts(iso):
    return mktime(iso8601.parse_date(iso).timetuple())*1000

def _date_ts(date):
    (y,m,d) = date.split("-")
    return int(mktime((int(y),int(m),int(d),12,0,0,0,0,-1)))*1000 # high noon

@login_required
def user(request):
    (local,domain) = request.user.username.split('@')
    return respond_to(request,{'text/html': 'apps/stats/user.html'},{'domain': domain})

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
def user_minutes_api(request,username=None):
    if username and username != request.user.username:
        return HttpResponseForbidden("You can't spy on others!")
    
    if username == None:
        username = request.user.username
    
    api = ac_api_client(request)
    p = {'sort1-type': 'asc','sort2-type': 'asc','sort1': 'date-created','sort2': 'date-closed','filter-type': 'meeting','filter-login':username}
    
    form = StatCaledarForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest()
    
    begin = form.cleaned_data['begin']
    end = form.cleaned_data['end']
    
    if begin != None:
        p['filter-gte-date-created'] = begin
    if end != None:
        p['filter-lt-date-created'] = end
    r = api.request('report-bulk-consolidated-transactions',p)
    
    series = []
    d_created  = None
    d_closed = None
    ms = 0
    curdate = None
    t_ms = 0
    rc = {}
    for row in r.et.xpath("//row"):
        rc[row.get('sco-id')] = True
        date_created_str = row.findtext("date-created")
        ts_created = _iso2ts(date_created_str)
        date_closed_str = row.findtext("date-closed")
        ts_closed = _iso2ts(date_closed_str)
        
        d1 = _iso2datesimple(date_created_str)
        if d_created == None:
            d_created = d1
            
        d2 = _iso2datesimple(date_closed_str)
        if d_closed == None:
            d_closed = d2
            
        if curdate == None:
            curdate = d1
            
        if curdate != d1:
            series.append([_date_ts(curdate),int(ms/60000)])
            ms = 0
            curdate = d1
            
        if d1 == d2: #same date
            diff = (ts_closed - ts_created)
            ms = ms + diff
            t_ms = t_ms + diff
        else: # meeting spanned midnight
            ts_date_ts = _date_ts(d2)
            ms = ms + (ts_date_ts - ts_created)
            series.append([_date_ts(d1),int(ms/60000)])
            t_ms = t_ms + ms
            curdate = d2
            ms = (ts_closed - ts_date_ts)
            
    if curdate != None and ms > 0:
        series.append([_date_ts(curdate),int(ms/60000)])
    
    return json_response({'data': sorted(series,key=lambda x: x[0]), 'rooms': len(rc.keys()), 'minutes': int(t_ms/60000)},request)

@login_required
def domain_minutes_api(request,domain):
    api = ac_api_client(request)
    p = {'sort': 'asc','sort1': 'date-created','filter-type': 'meeting'}
    
    form = StatCaledarForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest()
    
    begin = form.cleaned_data['begin']
    end = form.cleaned_data['end']
    
    if begin != None:
        p['filter-gte-date-created'] = begin
    if end != None:
        p['filter-lt-date-created'] = end
    r = api.request('report-bulk-consolidated-transactions',p)
    
    series = []
    d_created  = None
    d_closed = None
    ms = 0
    curdate = None
    t_ms = 0
    rc = {}
    uc = {}
    for row in r.et.xpath("//row"):
        login = row.findtext("login")
        if not login.endswith("@%s" % domain):
            continue
        
        rc[row.get('sco-id')] = True
        uc[row.get('principal-id')] = True
        date_created_str = row.findtext("date-created")
        ts_created = _iso2ts(date_created_str)
        date_closed_str = row.findtext("date-closed")
        ts_closed = _iso2ts(date_closed_str)
        
        d1 = _iso2datesimple(date_created_str)
        if d_created == None:
            d_created = d1
            
        d2 = _iso2datesimple(date_closed_str)
        if d_closed == None:
            d_closed = d2
            
        if curdate == None:
            curdate = d1
            
        if curdate != d1:
            series.append([_date_ts(curdate),int(ms/60000)])
            ms = 0
            curdate = d1
            
        if d1 == d2: #same date
            diff = (ts_closed - ts_created)
            ms = ms + diff
            t_ms = t_ms + diff
        else: # meeting spanned midnight
            ts_date_ts = _date_ts(d2)
            ms = ms + (ts_date_ts - ts_created)
            series.append([_date_ts(d1),int(ms/60000)])
            t_ms = t_ms + ms
            curdate = d2
            ms = (ts_closed - ts_date_ts)
            
    if curdate != None and ms > 0:
        series.append([_date_ts(curdate),int(ms/60000)])
    
    return json_response({'data': sorted(series,key=lambda x: x[0]), 'rooms': len(rc.keys()), 'users': len(uc.keys()), 'minutes': int(t_ms/60000)},request)


@login_required
def room_minutes_api(request,rid):
    room = get_object_or_404(Room,pk=rid)
    if not room.creator == request.user:
        return HttpResponseForbidden("You can only look at statistics for your own rooms!")
    
    api = ac_api_client(request)
    p = {'sort': 'asc','sort1': 'date-created','filter-type': 'meeting','filter-sco-id': room.sco_id}
    
    form = StatCaledarForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest()
    
    begin = form.cleaned_data['begin']
    end = form.cleaned_data['end']
    
    if begin != None:
        p['filter-gte-date-created'] = begin
    if end != None:
        p['filter-lt-date-created'] = end
    r = api.request('report-bulk-consolidated-transactions',p)
    
    series = []
    d_created  = None
    d_closed = None
    ms = 0
    curdate = None
    t_ms = 0
    uc = {}
    for row in r.et.xpath("//row"):
        uc[row.get('principal-id')] = True
        date_created_str = row.findtext("date-created")
        ts_created = _iso2ts(date_created_str)
        date_closed_str = row.findtext("date-closed")
        ts_closed = _iso2ts(date_closed_str)
        
        d1 = _iso2datesimple(date_created_str)
        if d_created == None:
            d_created = d1
            
        d2 = _iso2datesimple(date_closed_str)
        if d_closed == None:
            d_closed = d2
            
        if curdate == None:
            curdate = d1
            
        if curdate != d1:
            series.append([_date_ts(curdate),int(ms/60000)])
            ms = 0
            curdate = d1
            
        if d1 == d2: #same date
            diff = (ts_closed - ts_created)
            ms = ms + diff
            t_ms = t_ms + diff
        else: # meeting spanned midnight
            ts_date_ts = _date_ts(d2)
            ms = ms + (ts_date_ts - ts_created)
            series.append([_date_ts(d1),int(ms/60000)])
            t_ms = t_ms + ms
            curdate = d2
            ms = (ts_closed - ts_date_ts)
            
    if curdate != None and ms > 0:
        series.append([_date_ts(curdate),int(ms/60000)])
    
    return json_response({'data': sorted(series,key=lambda x: x[0]), 'users': len(uc.keys()), 'minutes': int(t_ms/60000)},request)