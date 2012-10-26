"""
Created on Jan 31, 2011

@author: leifj
"""
from celery.utils import deprecated
from meetingtools.apps.sco.models import get_sco, get_sco_shortcuts
from meetingtools.apps.room.models import Room
from meetingtools.multiresponse import respond_to, redirect_to, json_response
from meetingtools.apps.room.forms import DeleteRoomForm,\
    CreateRoomForm, ModifyRoomForm, TagRoomForm
from django.shortcuts import get_object_or_404
from meetingtools.ac import ac_api_client
import re
from django.contrib.auth.decorators import login_required
import logging
from pprint import pformat
from meetingtools.utils import session, base_url
import time
from django.conf import settings
from django.utils.datetime_safe import datetime
from django.http import HttpResponseRedirect
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django_co_acls.models import allow, acl, clear_acl
from meetingtools.ac.api import ACPClient
from tagging.models import Tag, TaggedItem
import random, string
from django.utils.feedgenerator import rfc3339_date
from django.views.decorators.cache import never_cache
from meetingtools.apps.cluster.models import acc_for_user
from django.contrib.auth.models import User
import iso8601
from celery.execute import send_task
from meetingtools.apps.room.tasks import start_user_counts_poll

def _user_meeting_folder(request,acc):
    if not session(request,'my_meetings_sco_id'):
        with ac_api_client(acc) as api:
            userid = request.user.username
            folders = api.request('sco-search-by-field',{'filter-type': 'folder','field':'name','query':userid}).et.xpath('//sco[folder-name="User Meetings"]')
            logging.debug("user meetings folder: "+pformat(folders))
            #folder = next((f for f in folders if f.findtext('.//folder-name') == 'User Meetings'), None)
            if folders and len(folders) > 0:
                session(request,'my_meetings_sco_id',folders[0].get('sco-id'))
    
    return session(request,'my_meetings_sco_id')

def _user_templates(request,acc,folder_sco):
    templates = []
    with ac_api_client(acc) as api:
        if folder_sco:
            my_templates = api.request('sco-contents',{'sco-id': folder_sco.sco_id,'filter-type': 'folder'}).et.xpath('.//sco[folder-name="My Templates"][0]')
            if my_templates and len(my_templates) > 0:
                my_templates_sco_id = my_templates[0].get('sco_id')
                meetings = api.request('sco-contents',{'sco-id': my_templates_sco_id,'filter-type': 'meeting'})
                if meetings:
                    templates += [(get_sco(acc,r.get('sco-id')),r.findtext('name')) for r in meetings.et.findall('.//sco')]
        
        shared_templates_sco = get_sco_shortcuts(acc,'shared-meeting-templates')
        shared_templates = api.request('sco-contents',{'sco-id': shared_templates_sco.sco_id,'filter-type': 'meeting'})
        if shared_templates:
            templates += [(get_sco(acc,r.get('sco-id')).id,r.findtext('name')) for r in shared_templates.et.findall('.//sco')]
            
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
                       'baseurl': base_url(request),
                       'active': True,
                       })

def _init_update_form(request,form,acc,folder_sco):
    if form.fields.has_key('urlpath'):
        url = base_url(request)
        form.fields['urlpath'].widget.prefix = url
    if form.fields.has_key('source_sco'):
        form.fields['source_sco'].widget.choices = [('','-- select template --')]+[r for r in _user_templates(request,acc,folder_sco)]

def _update_room(request, room, data=dict(), acc=None):
    params = {'type':'meeting'}

    if acc is None:
        acc = acc_for_user(request.user)

    for attr,param in (('sco','sco-id'),('folder_sco','folder-id'),('source_sco','source-sco-id'),('urlpath','url-path'),('name','name'),('description','description')):
        v = None
        if hasattr(room,attr):
            v = getattr(room,attr) 
        logging.debug("%s,%s = %s" % (attr,param,repr(v)))
        if data.has_key(attr) and data[attr]:
            v = data[attr]
        
        if v:
            if isinstance(v,(str,unicode)):
                params[param] = v
            elif hasattr(v,'sco_id'):
                params[param] = v.sco_id # support ACObject instances
            elif hasattr(v,'__getitem__'):
                params[param] = v[0]
            else:
                params[param] = repr(v)
        
    logging.debug(pformat(params))
    with ac_api_client(acc) as api:
        r = api.request('sco-update', params, True)
        sco_elt = r.et.find(".//sco")
        if sco_elt:
            sco_id = sco_elt.get('sco-id')
            if sco_id:
                data['sco'] = get_sco(acc,sco_id)

            source_sco_id = r.et.find(".//sco").get('sco-source-id')
            if source_sco_id:
                data['source_sco'] = get_sco(acc,source_sco_id)

            room.sco = data['sco']
            room.save()

        sco_id = room.sco.sco_id

        assert(sco_id is not None and sco_id > 0)

        user_principal = api.find_user(room.creator.username)
        #api.request('permissions-reset',{'acl-id': sco_id},True)
        api.request('permissions-update',{'acl-id': sco_id,
                                          'principal-id': user_principal.get('principal-id'),
                                          'permission-id':'host'},True) # owner is always host

        if data.has_key('access'):
            access = data['access']
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
    
        room.deleted_sco = None # if we just cleaned a room we zero out the deleted_sco_id field to indicate the room is now ready for use
        room.save() # a second save here to avoid races
        return room

@never_cache
@login_required
def create(request):
    acc = acc_for_user(request.user)
    my_meetings_sco = get_sco(acc,_user_meeting_folder(request,acc))
    template_sco_id = acc.default_template_sco_id
    if not template_sco_id:
        template_sco_id = settings.DEFAULT_TEMPLATE_SCO
    room = Room(creator=request.user,folder_sco=my_meetings_sco,source_sco=get_sco(acc,template_sco_id))
    what = "Create"
    title = "Create a new room"
    
    if request.method == 'POST':
        form = CreateRoomForm(request.POST,instance=room)
        _init_update_form(request, form, acc, my_meetings_sco)
        if form.is_valid():
            _update_room(request, room, form.cleaned_data)
            room = form.save()
            return redirect_to("/rooms#%d" % room.id)
    else:
        form = CreateRoomForm(instance=room)
        _init_update_form(request, form, acc, my_meetings_sco)
        
    return respond_to(request,{'text/html':'apps/room/create.html'},
        {'form':form,
         'formtitle': title,
         'cancelurl': '/rooms',
         'cancelname':'Cancel',
         'submitname':'%s Room' % what})

@never_cache
@login_required
def myroom(request):
    acc = acc_for_user(request.user)
    my_meetings_sco = get_sco(acc,_user_meeting_folder(request,acc))
    template_sco_id = acc.default_template_sco_id
    if not template_sco_id:
        template_sco_id = settings.DEFAULT_TEMPLATE_SCO
    template_sco = get_sco(acc,template_sco_id)
    room = None
    try:
        room = Room.by_name(acc,name=request.user.username)
    except MultipleObjectsReturned:
        raise ValueError("Oops - there seem to be multiple rooms with name '%s'" % request.user.username)
    except ObjectDoesNotExist:
        room = Room(creator=request.user,
                    folder_sco=my_meetings_sco,
                    name=request.user.username,
                    source_sco=template_sco)
        _update_room(request,room,dict(access='public'))

    if not room:
        raise ValueError("Opps - can't find your room")

    return _goto(request,room)

@never_cache
@login_required
def update(request,id):
    room = get_object_or_404(Room,pk=id)
    acc = room.sco.acc
    what = "Update"
    title = "Modify %s" % room.name
    
    if request.method == 'POST':
        form = ModifyRoomForm(request.POST,instance=room)
        _init_update_form(request, form, acc, room.folder_sco)
        if form.is_valid():
            _update_room(request, room, form.cleaned_data)
            room = form.save()
            return redirect_to("/rooms#%d" % room.id)
    else:
        form = ModifyRoomForm(instance=room)
        _init_update_form(request, form, acc, room.folder_sco)
        
    return respond_to(request,{'text/html':'apps/room/update.html'},
        {'form':form,
         'formtitle': title,
         'cancelurl': '/rooms#%d' % room.id,
         'cancelname': 'Cancel',
         'submitname':'%s Room' % what})

@deprecated
def _import_room(request,acc,r):
    modified = False
    room = None
    
    if room and (abs(room.lastupdate() - time.time()) < settings.IMPORT_TTL):
        return room
    
    if r.has_key('urlpath'):
        r['urlpath'] = r['urlpath'].strip('/')
    
    try:
        room = Room.by_sco(r['sco'])
        for key in ('sco','name','source_sco','urlpath','description','user_count','host_count'):
            if r.has_key(key) and hasattr(room,key):
                rv = getattr(room,key)
                if rv != r[key] and r[key] is not None and r[key]:
                    setattr(room,key,r[key])
                    modified = True
        
        if modified:
            logging.debug("+++ saving room ... %s" % pformat(room))
            room.save()
        
    except ObjectDoesNotExist:
        if r['folder_sco']:
            try:
                room = Room.objects.create(sco=r['sco'],
                                           source_sco=r['source_sco'],
                                           name=r['name'],
                                           urlpath=r['urlpath'],
                                           description=r['description'],
                                           creator=request.user,
                                           folder_sco=r['folder_sco'])
            except Exception,e:
                room = None
                pass
            
    if not room:
        return None
            
    logging.debug("+++ looking at user counts")
    with ac_api_client(acc) as api:
        userlist = api.request('meeting-usermanager-user-list',{'sco-id': room.sco.sco_id},False)
        if userlist.status_code() == 'ok':
            room.user_count = int(userlist.et.xpath("count(.//userdetails)"))
            room.host_count = int(userlist.et.xpath("count(.//userdetails/role[text() = 'host'])"))
            room.save()
        
    return room

@login_required
def list_rooms(request,username=None):
    user = request.user
    if username:
        try:
            user = User.objects.get(username=username)
        except ObjectDoesNotExist:
            user = None
            
    rooms = []
    if user:
        rooms = Room.objects.filter(creator=user).order_by('name').all()
    
    return respond_to(request,
                      {'text/html':'apps/room/list.html'},
                      {'title':'Your Rooms','edit':True,'active':len(rooms) == 1,'rooms':rooms})

@login_required
def unlock(request,id):
    room = get_object_or_404(Room,pk=id)
    room.unlock()
    return redirect_to("/rooms#%d" % room.id)

@login_required
def delete(request,id):
    room = get_object_or_404(Room,pk=id)
    if request.method == 'POST':
        form = DeleteRoomForm(request.POST)
        if form.is_valid():
            with ac_api_client(room.sco.acc) as api:
                api.request('sco-delete',{'sco-id':room.sco.sco_id},raise_error=True)
            clear_acl(room)
            del room.sco
            if room.folder_sco is not None:
                del room.folder_sco
            if room.deleted_sco is not None:
                del room.deleted_sco
            room.delete()
            return redirect_to("/rooms")
    else:
        form = DeleteRoomForm()
        
    return respond_to(request,{'text/html':'edit.html'},
        {'form':form,
         'formtitle': 'Delete %s' % room.name,
         'cancelurl': '/rooms',
         'cancelname':'Cancel',
         'submitname':'Delete Room'})

def _clean(request,room):
    with ac_api_client(room.sco.acc) as api:
        room.deleted_sco = room.sco
        room.save()
        api.request('sco-delete',{'sco-id':room.sco.sco_id},raise_error=False)
        room.sco = None
    return _update_room(request, room)

def occupation(request,rid):
    room = get_object_or_404(Room,pk=rid)
    with ac_api_client(room.sco.acc) as api:
        api.poll_user_counts(room)
        d = {'nusers': room.user_count, 'nhosts': room.host_count} 
        return respond_to(request,
                          {'text/html': 'apps/room/fragments/occupation.txt',
                           'application/json': json_response(d, request)},
                          d)

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
    if room.is_locked():
        return respond_to(request, {"text/html": "apps/room/retry.html"}, {'room': room, 'wait': 10})
    
    now = time.time()
    lastvisit = room.lastvisit()
    room.lastvisited = datetime.now()
    
    with ac_api_client(room.sco.acc) as api:
        api.poll_user_counts(room)
    if clean:
        # don't clean the room unless you get a good status code from the call to the usermanager api above
        if room.self_cleaning and room.user_count == 0:
            if (room.user_count == 0) and (abs(lastvisit - now) > settings.GRACE):
                room.lock("Locked for cleaning")
                try:
                    room = _clean(request,room)
                finally:
                    room.unlock()
                
        if room.host_count == 0 and room.allow_host:
            return respond_to(request, {"text/html": "apps/room/launch.html"}, {'room': room})
    else:
        room.save()
    
    key = None
    if request.user.is_authenticated():
        key = _random_key(20)
        user_principal = api.find_user(request.user.username)
        principal_id =  user_principal.get('principal-id')
        with ac_api_client(room.sco.acc) as api:
            api.request("user-update-pwd",{"user-id": principal_id, 'password': key,'password-verify': key},True)
            if promote and room.self_cleaning:
                if user_principal:
                    api.request('permissions-update',{'acl-id': room.sco.sco_id,'principal-id': user_principal.get('principal-id'),'permission-id':'host'},True)
    
    r = api.request('sco-info',{'sco-id':room.sco.sco_id},True)
    urlpath = r.et.findtext('.//sco/url-path')
    start_user_counts_poll(room,10)
    if key:
        try:
            user_client = ACPClient(room.sco.acc.api_url, request.user.username, key, cache=False)
            return user_client.redirect_to(room.sco.acc.url+urlpath)
        except Exception,e:
            pass
    return HttpResponseRedirect(room.sco.acc.url+urlpath)
    
## Tagging

def _room2dict(request,room):
    return {'name':room.name,
            'description':room.description,
            'user_count':room.nusers(),
            'host_count':room.nhosts(),
            'updated': rfc3339_date(room.lastupdated),
            'self_cleaning': room.self_cleaning,
            'url': base_url(request,room.go_url())}

# should not require login
def list_by_tag(request,tn):
    tags = tn.split('+')
    rooms = TaggedItem.objects.get_by_model(Room, tags).order_by('name').all()
    title = 'Rooms tagged with %s' % " and ".join(tags)
    return respond_to(request,
                      {'text/html':'apps/room/list.html',
                       'application/json': json_response([_room2dict(request,room) for room in rooms],request)},
                      {'title':title,
                       'description':title ,
                       'edit':False,
                       'active':len(rooms) == 1,
                       'baseurl': base_url(request),
                       'tagstring': tn,
                       'rooms':rooms})

    
def widget(request,tags=None):
    title = 'Meetingtools jQuery widget'
    return respond_to(request,{'text/html':'apps/room/widget.html'},{'title': title,'tags':tags})
    
def _can_tag(request,tag):
    if tag in ('selfcleaning','cleaning','public','private'):
        return False,"'%s' is reserved" % tag
    # XXX implement access model for tags here soon
    return True,""

@never_cache
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
            for tag in re.split('[,\s]+',form.cleaned_data['tag']):
                tag = tag.strip()
                ok,reason = _can_tag(request,tag)
                if ok:
                    Tag.objects.add_tag(room, tag)
                else:
                    form._errors['tag'] = form.error_class([u'%s ... please choose another tag!' % reason])
    else:
        form = TagRoomForm()
    
    tags = Tag.objects.get_for_object(room)
    tn = "+".join([t.name for t in tags])
    return respond_to(request, 
                      {'text/html': "apps/room/tag.html"}, 
                      {'form': form,
                       'formtitle': 'Add Tag',
                       'cancelurl': '/rooms#%d' % room.id,
                       'cancelname':'Done',
                       'submitname': 'Add Tag',
                       'room': room,
                       'tagstring': tn,
                       'tags': tags})

def room_recordings(request,room):
    acc = room.sco.acc
    with ac_api_client(acc) as api:
        r = api.request('sco-expanded-contents',{'sco-id': room.sco.sco_id,'filter-icon':'archive'},True)
        return [{'published': False,
                 'name': sco_elt.findtext('name'),
                 'sco': get_sco(acc,sco_elt.get('sco-id')),
                 'url': room.sco.acc.make_url(sco_elt.findtext('url-path')),
                 'dl': room.sco.acc.make_dl_url(sco_elt.findtext('url-path')),
                 'description':  sco_elt.findtext('description'),
                 'date_created': iso8601.parse_date(sco_elt.findtext('date-created')),
                 'date_modified': iso8601.parse_date(sco_elt.findtext('date-modified'))} for sco_elt in r.et.findall(".//sco")] + [
            {'published': True,
             'ar': ar,
             'name': ar.name,
             'description': ar.description,
             'sco': ar.sco,
             'url': room.sco.acc.make_url(ar.urlpath),
             'dl': room.sco.acc.make_url(ar.urlpath),
             'date_created': ar.timecreated,
             'date_modified': ar.lastupdated} for ar in room.archives.all()
        ]
@login_required
def recordings(request,rid):
    room = get_object_or_404(Room,pk=rid)
    return respond_to(request,
                      {'text/html': 'apps/room/recordings.html'},
                      {'recordings': room_recordings(request,room),'room':room})