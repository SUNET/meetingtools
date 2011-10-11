'''
Created on Jan 31, 2011

@author: leifj
'''
from meetingtools.apps.room.models import Room, ACCluster
from meetingtools.multiresponse import respond_to, redirect_to, json_response,\
    timeAsrfc822
from meetingtools.apps.room.forms import DeleteRoomForm,\
    CreateRoomForm, ModifyRoomForm, TagRoomForm
from django.shortcuts import get_object_or_404
from meetingtools.ac import ac_api_client, api
import re
from meetingtools.apps import room
from django.contrib.auth.decorators import login_required
import logging
from pprint import pformat
from meetingtools.utils import session
import time
from meetingtools.settings import GRACE, BASE_URL, DEFAULT_TEMPLATE_SCO
from django.utils.datetime_safe import datetime
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist
from django_co_acls.models import allow, deny, acl, clear_acl
from meetingtools.ac.api import ACPClient
from tagging.models import Tag, TaggedItem
import random, string
from django.utils.feedgenerator import rfc3339_date
from django.views.decorators.cache import cache_control, never_cache

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
            rooms = [{'sco_id': r.get('sco-id'),
                     'name': r.findtext('name'),
                     'source_sco_id': r.get('source-sco-id'),
                     'urlpath': r.findtext('url-path'),
                     'description': r.findtext('description')} for r in meetings.et.findall('.//sco')]
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
    return respond_to(request,
                      {'text/html':'apps/room/list.html'},
                      {'user':request.user,
                       'rooms':[room],
                       'title': room.name,
                       'active': True,
                       })

def _init_update_form(request,form,acc,my_meetings_sco_id):
    if form.fields.has_key('urlpath'):
        url = BASE_URL
        form.fields['urlpath'].widget.prefix = url.rstrip('/')+"/"
    if form.fields.has_key('source_sco_id'):
        form.fields['source_sco_id'].widget.choices = [('','-- select template --')]+[r for r in _user_templates(request,acc,my_meetings_sco_id)]

def _update_room(request, room, form=None):        
    api = ac_api_client(request, room.acc)
    params = {'type':'meeting'}
    
    for attr,param in (('sco_id','sco-id'),('folder_sco_id','folder-id'),('source_sco_id','source-sco-id'),('urlpath','url-path'),('name','name'),('description','description')):
        v = None
        if hasattr(room,attr):
            v = getattr(room,attr) 
        logging.debug("%s,%s = %s" % (attr,param,v))
        if form and form.cleaned_data.has_key(attr) and form.cleaned_data[attr]:
            v = form.cleaned_data[attr]
        
        if v:
            if isinstance(v,(str,unicode)):
                params[param] = v
            elif hasattr(v,'__getitem__'):
                params[param] = v[0]
            else:
                params[param] = repr(v)
        
    logging.debug(pformat(params))
    r = api.request('sco-update', params, True)
    
    sco_id = r.et.find(".//sco").get('sco-id')
    if form:
        form.cleaned_data['sco_id'] = sco_id
        form.cleaned_data['source_sco_id'] = r.et.find(".//sco").get('sco-source-id')
    
    room.sco_id = sco_id
    room.save()
    
    user_principal = api.find_user(room.creator.username)
    #api.request('permissions-reset',{'acl-id': sco_id},True)
    api.request('permissions-update',{'acl-id': sco_id,'principal-id': user_principal.get('principal-id'),'permission-id':'host'},True) # owner is always host
    
    if form:
        if form.cleaned_data.has_key('access'):
            access = form.cleaned_data['access']
            if access == 'public':
                allow(room,'anyone','view-hidden')
            elif access == 'private':
                allow(room,'anyone','remove')
    
    # XXX figure out how to keep the room permissions in sync with the AC permissions
    for ace in acl(room):
        principal_id = None
        if ace.group:
            principal = api.find_group(ace.group.name)
            if principal:
                principal_id = principal.get('principal-id')
        elif ace.user:
            principal = api.find_user(ace.user.username)
            if principal:
                principal_id = principal.get('principal-id')
        else:
            principal_id = "public-access"
        
        if principal_id:  
            api.request('permissions-update',{'acl-id': room.sco_id, 'principal-id': principal_id, 'permission-id': ace.permission},True)

    return room

@never_cache
@login_required
def create(request):
    acc = _acc_for_user(request.user)
    my_meetings_sco_id = _user_meeting_folder(request,acc)
    template_sco_id = acc.default_template_sco_id
    if not template_sco_id:
        template_sco_id = DEFAULT_TEMPLATE_SCO
    room = Room(creator=request.user,acc=acc,folder_sco_id=my_meetings_sco_id,source_sco_id=template_sco_id)
    what = "Create"
    title = "Create a new room"
    
    if request.method == 'POST':
        form = CreateRoomForm(request.POST,instance=room)
        _init_update_form(request, form, acc, room.folder_sco_id)
        if form.is_valid():
            _update_room(request, room, form)
            room = form.save()
            return redirect_to("/rooms#%d" % room.id)
    else:
        form = CreateRoomForm(instance=room)
        _init_update_form(request, form, acc, room.folder_sco_id)
        
    return respond_to(request,{'text/html':'apps/room/create.html'},{'form':form,'formtitle': title,'cancelname':'Cancel','submitname':'%s Room' % what})

@never_cache
@login_required
def update(request,id):
    room = get_object_or_404(Room,pk=id)
    acc = room.acc
    what = "Update"
    title = "Modify %s" % room.name
    
    if request.method == 'POST':
        form = ModifyRoomForm(request.POST,instance=room)
        _init_update_form(request, form, acc, room.folder_sco_id)
        if form.is_valid():
            _update_room(request, room, form)
            room = form.save()
            return redirect_to("/rooms#%d" % room.id)
    else:
        form = ModifyRoomForm(instance=room)
        _init_update_form(request, form, acc, room.folder_sco_id)
        
    return respond_to(request,{'text/html':'apps/room/update.html'},{'form':form,'formtitle': title,'cancelname': 'Cancel','submitname':'%s Room' % what})

def _import_room(request,acc,r):
    modified = False
    room = None
    try:
        room = Room.objects.get(sco_id=r['sco_id'],acc=acc)
    except ObjectDoesNotExist:
        if r['folder_sco_id']:
            room = Room.objects.create(sco_id=r['sco_id'],acc=acc,creator=request.user,folder_sco_id=r['folder_sco_id'])
        
    if not room:
        return None
        
    api = ac_api_client(request,acc)
    userlist = api.request('meeting-usermanager-user-list',{'sco-id': room.sco_id},False)
    r['user_count'] = 0
    r['host_count'] = 0
    if userlist.status_code() == 'ok':
        r['user_count'] = int(userlist.et.xpath("count(.//userdetails)"))
        r['host_count'] = int(userlist.et.xpath("count(.//userdetails/role[text() = 'host'])"))
        
    #logging.debug(pformat(room))
    
    if r.has_key('urlpath'):
        r['urlpath'] = r['urlpath'].strip('/')
    
    for key in ('sco_id','name','source_sco_id','urlpath','description','user_count','host_count'):
        if r.has_key(key) and hasattr(room,key):
            rv = getattr(room,key)
            if rv != r[key] and r[key] != None and r[key] != '':
                setattr(room,key,r[key])
                modified = True
    
    #logging.debug(pformat(room))
        
    if modified:
        logging.debug("saving ... %s" % pformat(room))
        room.save()
    
    return room

@login_required
def user_rooms(request):
    acc = _acc_for_user(request.user)
    my_meetings_sco_id = _user_meeting_folder(request,acc)
    user_rooms = _user_rooms(request,acc,my_meetings_sco_id)
    
    ar = []
    for r in user_rooms:
        logging.debug(pformat(r))
        ar.append(int(r['sco_id']))
    
    for r in Room.objects.filter(creator=request.user).all():
        if (not r.sco_id in ar): # and (not r.self_cleaning): #XXX this logic isn't right!
            for t in Tag.objects.get_for_object(r):
                t.delete()
            r.delete() 
    
    for r in user_rooms:
        r['folder_sco_id'] = my_meetings_sco_id
        room = _import_room(request,acc,r)
        
    rooms = Room.objects.filter(creator=request.user).order_by('name').all()
    return respond_to(request,
                      {'text/html':'apps/room/list.html'},
                      {'title':'Your Rooms','edit':True,'active':len(rooms) == 1,'rooms':rooms})

@login_required
def delete(request,id):
    room = get_object_or_404(Room,pk=id)
    if request.method == 'POST':
        form = DeleteRoomForm(request.POST)
        if form.is_valid():
            api = ac_api_client(request,room.acc)
            api.request('sco-delete',{'sco-id':room.sco_id},raise_error=True)
            clear_acl(room)
            room.delete()
            
            return redirect_to("/rooms")
    else:
        form = DeleteRoomForm()
        
    return respond_to(request,{'text/html':'edit.html'},{'form':form,'formtitle': 'Delete %s' % room.name,'cancelname':'Cancel','submitname':'Delete Room'})      

def _clean(request,room):
    api = ac_api_client(request, room.acc)
    api.request('sco-delete',{'sco-id':room.sco_id},raise_error=False)
    room.sco_id = None
    return _update_room(request, room)

def go_by_id(request,id):
    room = get_object_or_404(Room,pk=id)
    return goto(request,room)

def go_by_path(request,path):
    room = get_object_or_404(Room,urlpath=path)
    return goto(request,room)
        
@login_required
def promote_and_launch(request,rid):
    room = get_object_or_404(Room,pk=rid)
    return _goto(request,room,clean=False,promote=True)

def launch(request,rid):
    room = get_object_or_404(Room,pk=rid)
    return _goto(request,room,clean=False)
        
def goto(request,room):
    return _goto(request,room,clean=True)

def _random_key(length=20):
    rg = random.SystemRandom()
    alphabet = string.letters + string.digits
    return str().join(rg.choice(alphabet) for _ in range(length))

def _goto(request,room,clean=True,promote=False):
    api = ac_api_client(request, room.acc)
    now = time.time()
    lastvisit = room.lastvisit()
    room.lastvisited = datetime.now()
    
    if clean:
        userlist = api.request('meeting-usermanager-user-list',{'sco-id': room.sco_id},False)
        room.user_count = 0
        room.host_count = 0
        if userlist.status_code() == 'ok':
            room.user_count = int(userlist.et.xpath("count(.//userdetails)"))
            room.host_count = int(userlist.et.xpath("count(.//userdetails/role[text() = 'host'])"))
        
        #session_info = api.request('report-meeting-sessions',{'sco-id':room.sco_id})
        #room.user_count = _nusers(session_info)
        logging.debug("---------- nusers: %s" % room.user_count)
        room.save()
        if room.self_cleaning:
            if (room.user_count == 0) and (abs(lastvisit - now) > GRACE):        
                room = _clean(request,room)
                
            if room.host_count == 0 and room.allow_host:
                return respond_to(request, {"text/html": "apps/room/launch.html"}, {'room': room})
    else:
        room.save()
    
    key = None
    if request.user.is_authenticated():
        key = _random_key(20)
        user_principal = api.find_user(request.user.username)
        principal_id =  user_principal.get('principal-id')
        api.request("user-update-pwd",{"user-id": principal_id, 'password': key,'password-verify': key},True)
        if promote and room.self_cleaning:
            if user_principal:
                api.request('permissions-update',{'acl-id': room.sco_id,'principal-id': user_principal.get('principal-id'),'permission-id':'host'},True)
    
    r = api.request('sco-info',{'sco-id':room.sco_id},True)
    urlpath = r.et.findtext('.//sco/url-path')
    if key:
        user_client = ACPClient(room.acc.api_url, request.user.username, key, cache=False)
        return user_client.redirect_to(room.acc.url+urlpath)
    else:
        return HttpResponseRedirect(room.acc.url+urlpath)
    
## Tagging

def _room2dict(room):
    return {'name':room.name,
            'description':room.description,
            'user_count':room.nusers(),
            'host_count':room.nhosts(),
            'updated': rfc3339_date(room.lastupdated),
            'self_cleaning': room.self_cleaning,
            'url': room.go_url()}

# should not require login
def list_by_tag(request,tn):
    tags = tn.split('+')
    rooms = TaggedItem.objects.get_by_model(Room, tags).order_by('name').all()
    for room in rooms:
        _import_room(request,room.acc,{'sco_id': room.sco_id})
    title = 'Rooms tagged with %s' % " and ".join(tags)
    return respond_to(request,
                      {'text/html':'apps/room/list.html',
                       'application/json': json_response([_room2dict(room) for room in rooms],request)},
                      {'title':title,
                       'description':title ,
                       'edit':False,
                       'active':len(rooms) == 1,
                       'baseurl': BASE_URL,
                       'tags': tn,
                       'rooms':rooms})
    
def widget(request,tags=None):
    title = 'Meetingtools jQuery widget'
    return respond_to(request,{'text/html':'apps/room/widget.html'},{'title': title,'tags':tags})
    
def _can_tag(request,tag):
    if tag in ('selfcleaning','cleaning','public','private'):
        return False,"'%s' is reserved" % tag
    # XXX implement access model for tags here soon
    return True,""

@login_required
def untag(request,rid,tag):
    room = get_object_or_404(Room,pk=rid)
    new_tags = []
    for t in Tag.objects.get_for_object(room):
        if t.name != tag:
            new_tags.append(t.name)
    
    Tag.objects.update_tags(room, ' '.join(new_tags))
    return redirect_to("/room/%d/tag" % room.id) 
    
@never_cache
@login_required  
def tag(request,rid):
    room = get_object_or_404(Room,pk=rid)
    if request.method == 'POST':
        form = TagRoomForm(request.POST)
        if form.is_valid():
            tag = form.cleaned_data['tag']
            ok,reason = _can_tag(request,tag)
            if ok:
                Tag.objects.add_tag(room, tag)
            else:
                form._errors['tag'] = form.error_class([u'%s ... please choose another tag!' % reason])
    else:
        form = TagRoomForm()
    
    return respond_to(request, 
                      {'text/html': "apps/room/tag.html"}, 
                      {'form': form,'formtitle': 'Add Tag','cancelname':'Done','submitname': 'Add Tag','room': room, 'tags': Tag.objects.get_for_object(room)})


from time import mktime
from feedparser import _parse_date as parse_date

def room_recordings(request,room):
    api = ac_api_client(request, room.acc)
    r = api.request('sco-expanded-contents',{'sco-id': room.sco_id,'filter-icon':'archive'},True)
    return [{'name': sco.findtext('name'),
             'sco_id': sco.get('sco-id'),
             'url': room.acc.make_url(sco.findtext('url-path')),
             'description':  sco.findtext('description'),
             'date_created': datetime.fromtimestamp(mktime(parse_date(sco.findtext('date-created')))),
             'date_modified': datetime.fromtimestamp(mktime(parse_date(sco.findtext('date-modified'))))} for sco in r.et.findall(".//sco")]

@login_required
def recordings(request,rid):
    room = get_object_or_404(Room,pk=rid)
    return respond_to(request,
                      {'text/html': 'apps/room/recordings.html'},
                      {'recordings': room_recordings(request,room),'room':room})