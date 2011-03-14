'''
Created on Jan 31, 2011

@author: leifj
'''
from meetingtools.apps.room.models import Room, ACCluster
from meetingtools.multiresponse import respond_to, redirect_to
from meetingtools.apps.room.forms import UpdateRoomForm, DeleteRoomForm
from django.shortcuts import get_object_or_404
from meetingtools.ac import ac_api_client, api
import re
from meetingtools.apps import room
from django.contrib.auth.decorators import login_required
from meetingtools.apps.auth.utils import groups
import logging
from pprint import pformat
from meetingtools.utils import session
import time
from meetingtools.settings import GRACE
from django.utils.datetime_safe import datetime
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist

def _acc_for_user(user):
    (local,domain) = user.username.split('@')
    if not domain:
        #raise Exception,"Improperly formatted user: %s" % user.username
        domain = "nordu.net" # testing with local accts only
    for acc in ACCluster.objects.all():
        for regex in acc.domain_match.split():
            if re.match(regex,domain):
                return acc
    raise Exception,"I don't know which cluster you belong to... (%s)" % user.username

def _user_meeting_folder(request,acc):
    if not session(request,'my_meetings_sco_id'):
        connect_api = ac_api_client(request, acc)
        userid = request.user.username
        folders = connect_api.request('sco-search-by-field',{'filter-type': 'folder','field':'name','query':userid}).et.xpath('//sco[folder-name="User Meetings"]')
        logging.debug("user meetings folder: "+pformat(folders))
        #folder = next((f for f in folders if f.findtext('.//folder-name') == 'User Meetings'), None)
        if folders and len(folders) > 0:
            session(request,'my_meetings_sco_id',folders[0].get('sco-id'))
    return session(request,'my_meetings_sco_id')

def _shared_templates_folder(request,acc):
    if not session(request,'shared_templates_sco_id'):
        connect_api = ac_api_client(request, acc)
        shared = connect_api.request('sco-shortcuts').et.xpath('.//sco[@type="shared-meeting-templates"]')
        logging.debug("shared templates folder: "+pformat(shared))
        #folder = next((f for f in folders if f.findtext('.//folder-name') == 'User Meetings'), None)
        if shared and len(shared) > 0:
            session(request,'shared_templates_sco_id',shared[0].get('sco-id'))
    return session(request,'shared_templates_sco_id')

def _user_rooms(request,acc,my_meetings_sco_id):
    rooms = []
    if my_meetings_sco_id:
        connect_api = ac_api_client(request, acc)
        meetings = connect_api.request('sco-expanded-contents',{'sco-id': my_meetings_sco_id,'filter-type': 'meeting'})
        if meetings:
            rooms = [(r.get('sco-id'),r.findtext('name'),r.get('source-sco-id'),r.findtext('url-path')) for r in meetings.et.findall('.//sco')]
    return rooms

def _user_templates(request,acc,my_meetings_sco_id):
    templates = []
    connect_api = ac_api_client(request, acc)
    if my_meetings_sco_id:
        my_templates = connect_api.request('sco-contents',{'sco-id': my_meetings_sco_id,'filter-type': 'folder'}).et.xpath('.//sco[folder-name="My Templates"][0]')
        if my_templates and len(my_templates) > 0:
            my_templates_sco_id = my_templates[0].get('sco_id')
            meetings = connect_api.request('sco-contents',{'sco-id': my_templates_sco_id,'filter-type': 'meeting'})
            if meetings:
                templates = templates + [(r.get('sco-id'),r.findtext('name')) for r in meetings.et.findall('.//sco')]
    
    shared_templates_sco_id = _shared_templates_folder(request, acc)
    if shared_templates_sco_id:
        shared_templates = connect_api.request('sco-contents',{'sco-id': shared_templates_sco_id,'filter-type': 'meeting'})
        if shared_templates:
            templates = templates + [(r.get('sco-id'),r.findtext('name')) for r in shared_templates.et.findall('.//sco')]
            
    return templates

def _find_current_session(session_info):
    for r in session_info.et.xpath('//row'):
        #logging.debug(pformat(etree.tostring(r)))
        end = r.findtext('date-end')
        if end is None:
            return r
    return None

def _nusers(session_info):
    cur = _find_current_session(session_info)
    if cur is not None:
        return cur.get('num-participants')
    else:
        return 0

@login_required
def view(request,id):
    room = get_object_or_404(Room,pk=id)
    api = ac_api_client(request,room.acc)
    room_info = api.request('sco-info',{'sco-id':room.sco_id},raise_error=True)
    perm_info = api.request('permissions-info',{'acl-id':room.sco_id,'filter-principal-id': 'public-access'},raise_error=True)
    session_info = api.request('report-meeting-sessions',{'sco-id':room.sco_id},raise_error=True)
    
    room.name = room_info.et.findtext('.//sco/name')
    room.save()
    return respond_to(request,
                      {'text/html':'apps/room/view.html'},
                      {'user':request.user,
                       'room':room,
                       'permission':  perm_info.et.find('.//principal').get('permission-id'),       
                       'nusers': _nusers(session_info)
                       })

def _init_update_form(request,form,acc,my_meetings_sco_id):
    form.fields['participants'].widget.choices = [('','-- anyone --')]+[(g,g) for g in groups(request)]
    form.fields['presenters'].widget.choices = [('','-- nobody --')]+[(g,g) for g in groups(request)]
    form.fields['hosts'].widget.choices = [('','-- nobody --')]+[(g,g) for g in groups(request)]
    form.fields['source_sco_id'].widget.choices = [('','-- select template --')]+[r for r in _user_templates(request,acc,my_meetings_sco_id)]

@login_required
def _update_room(request, room):
    api = ac_api_client(request, room.acc)
    params = {'type':'meeting', 
              'name':room.name, 
              'folder-id': room.folder_sco_id, 
              'source-sco-id': room.source_sco_id, 
              'url-path':room.urlpath}
    
    if room.sco_id:
        params['sco-id'] = room.sco_id
    r = api.request('sco-update', params, raise_error=True)
    
    room.sco_id = r.et.find(".//sco").get('sco-id')
    room.source_sco_id = r.et.find(".//sco").get('sco-source-id')
    room.save()
    #room = _import_room(params['sco-id'], params['name'], params['source-sco-id'], params['url-path'], request.user, acc)
    return room

@login_required
def update(request,id=None):
    if id:
        room = get_object_or_404(Room,pk=id)
        acc = room.acc
        what = "Update"
        title = "Modify %s" % room.name
        update = True
    else:
        acc = _acc_for_user(request.user)
        my_meetings_sco_id = _user_meeting_folder(request,acc)
        room = Room(creator=request.user,acc=acc,folder_sco_id=my_meetings_sco_id)
        what = "Create"
        title = "Create a new room"
        update = False
    
    if request.method == 'POST':
        form = UpdateRoomForm(request.POST,instance=room)
        _init_update_form(request, form, acc, room.folder_sco_id)
        if form.is_valid():
            room = _update_room(request, room)
            room = form.save()
            return redirect_to("/rooms#%d" % room.id)
    else:
        form = UpdateRoomForm(instance=room)
        _init_update_form(request, form, acc, room.folder_sco_id)
        if update:
            form.fields['urlpath'].widget.attrs['readonly'] = True
        
    return respond_to(request,{'text/html':'edit.html'},{'form':form,'formtitle': title,'submitname':'%s Room' % what})

def _import_room(request,acc,sco_id,source_sco_id,folder_sco_id,name,urlpath):
    modified = False
    try:
        room = Room.objects.get(sco_id=sco_id,acc=acc)
    except ObjectDoesNotExist:
        room = Room.objects.create(sco_id=sco_id,acc=acc,creator=request.user,folder_sco_id=folder_sco_id)
        
    logging.debug(pformat(room))
    
    if room.name != name and name:
        room.name = name
        modified = True
    
    if room.sco_id != sco_id and sco_id:
        room.sco_id = sco_id
        modified = True
    
    if not room.source_sco_id and source_sco_id:
        room.source_sco_id = source_sco_id
        modified = True
        
    if urlpath:
        urlpath = urlpath.strip('/')
        
    if room.urlpath != urlpath and urlpath:
        room.urlpath = urlpath
        modified = True
        
    #if '/' in room.urlpath:
    #    room.urlpath = urlpath.strip('/')
    #    modified = True
    
    logging.debug(pformat(room))
        
    if modified:
        logging.debug("saving ... %s" % pformat(room))
        room.save()
    
    return room

@login_required
def list(request):
    acc = _acc_for_user(request.user)
    my_meetings_sco_id = _user_meeting_folder(request,acc)
    user_rooms = _user_rooms(request,acc,my_meetings_sco_id)
    
    ar = []
    for (sco_id,name,source_sco_id,urlpath) in user_rooms:
        logging.debug("%s %s %s %s" % (sco_id,name,source_sco_id,urlpath))
        room = _import_room(request,acc,sco_id,source_sco_id,my_meetings_sco_id,name,urlpath)
        ar.append(int(sco_id))
    
    #logging.debug(pformat(ar))
        
    for r in Room.objects.filter(creator=request.user).all():
        #logging.debug(pformat(r))
        if (not r.sco_id in ar) and (not r.self_cleaning):
            r.delete() 
    return respond_to(request,{'text/html':'apps/room/list.html'},{'user':request.user,'rooms':Room.objects.filter(creator=request.user).all()})

def rooms_by_group(request,group):
    for room in Room.objects.filter(participants=group):
        pass

@login_required
def delete(request,id):
    room = get_object_or_404(Room,pk=id)
    if request.method == 'POST':
        form = DeleteRoomForm(request.POST)
        if form.is_valid():
            api = ac_api_client(request,room.acc)
            api.request('sco-delete',{'sco-id':room.sco_id},raise_error=True)
            room.delete()
            return redirect_to("/rooms")
    else:
        form = DeleteRoomForm()
        
    return respond_to(request,{'text/html':'edit.html'},{'form':form,'formtitle': 'Delete %s' % room.name,'submitname':'Delete Room'})      

def _clean(request,room):
    api = ac_api_client(request, room.acc)
    api.request('sco-delete',{'sco-id':room.sco_id},raise_error=True)
    room.sco_id = None
    return _update_room(request, room)

def go_by_id(request,id):
    room = get_object_or_404(Room,pk=id)
    return goto(request,room)

def go_by_path(request,path):
    room = get_object_or_404(Room,urlpath=path)
    return goto(request,room)
        
def goto(request,room):
    api = ac_api_client(request, room.acc)
    session_info = api.request('report-meeting-sessions',{'sco-id':room.sco_id})
    
    now = time.time()
    if room.self_cleaning:
        if (_nusers(session_info) == 0) and (abs(room.lastvisit() - now) > GRACE):
            room = _clean(request,room)
    
    room.lastvisited = datetime.now()
    room.save()
    
    r = api.request('sco-info',{'sco-id':room.sco_id})
    urlpath = r.et.findtext('.//sco/url-path')
    return HttpResponseRedirect(room.acc.url+urlpath) #in this case we want the absolute URL
    