'''
Created on Jan 18, 2012

@author: leifj
'''
from celery.task import periodic_task
from celery.schedules import crontab
from meetingtools.apps.cluster.models import ACCluster
from meetingtools.ac import ac_api_client, ac_api_client_nocache,\
    ac_api_client_direct
from meetingtools.apps.room.models import Room
import iso8601
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
import logging
from datetime import datetime,timedelta
from lxml import etree

def _owner_username(api,sco):
    logging.debug(sco)
    key = '_sco_owner_%s' % sco.get('sco-id')
    logging.debug(key)
    try:
        if cache.get(key) is None:
            fid = sco.get('folder-id')
            if not fid:
                logging.debug("No folder-id")
                return None
            
            folder_id = int(fid)
            r = api.request('sco-info',{'sco-id':folder_id},False)
            if r.status_code() == 'no-data':
                return None
            
            parent = r.et.xpath("//sco")[0]
            logging.debug("p %s",repr(parent))
            logging.debug("r %s",etree.tostring(parent))
            name = None
            if parent:
                logging.debug("parent: %s" % parent)
                if parent.findtext('name') == 'User Meetings':
                    name = sco.findtext('name')
                else:
                    name = _owner_username(api,parent)
                
                cache.set(key,name)
                
        return cache.get(key)
    except Exception,e:
        logging.debug(e)
        return None

def _extended_info(api,sco_id):
    r = api.request('sco-info',{'sco-id':sco_id},False)
    if r.status_code == 'no-data':
        return None
    return (r.et,_owner_username(api,r.et.xpath('//sco')[0]))
    
def _import_one_room(acc,api,row):
    sco_id = int(row.get('sco-id'))
    last = iso8601.parse_date(row.findtext("date-modified[0]"))
    room = None
    
    try:
        room = Room.objects.get(acc=acc,deleted_sco_id=sco_id)
        if room != None:
            return # We hit a room in the process of being cleaned - let it simmer until next pass
    except ObjectDoesNotExist:
        pass
    except Exception,e:
        logging.debug(e)
        return
    
    try:
        logging.debug("finding acc=%s,sco_id=%d in our DB" % (acc,sco_id))
        room = Room.objects.get(acc=acc,sco_id=sco_id)
        if room.deleted_sco_id != None:
            return # We hit a room in the process of being cleaned - let it simmer until next pass
        room.trylock()
    except ObjectDoesNotExist:
        pass
    
    last = last.replace(tzinfo=None)
    lastupdated = None
    if room:
        lastupdated = room.lastupdated.replace(tzinfo=None) # make the compare work - very ugly
    logging.debug("last %s" % last)
    logging.debug("lastupdated %s" % lastupdated)
    if not room or lastupdated < last:
        (r,username) = _extended_info(api, sco_id)
        logging.debug("owner: %s" % username)
        if username is None:
            return
        
        urlpath = row.findtext("url[0]").strip("/")
        name = row.findtext('name[0]')
        description = row.findtext('description[0]')
        folder_sco_id = int(r.xpath('//sco[0]/@folder-id') or 0) or None
        source_sco_id = int(r.xpath('//sco[0]/@source-sco-id') or 0) or None
            
        if room == None:   
            user,created = User.objects.get_or_create(username=username)
            if created:
                user.set_unusable_password()
            room = Room.objects.create(acc=acc,sco_id=sco_id,creator=user,name=name,description=description,folder_sco_id=folder_sco_id,source_sco_id=source_sco_id,urlpath=urlpath)
            room.trylock()
        else:
            room.folder_sco_id = folder_sco_id
            room.source_sco_id = source_sco_id
            room.description = description
            room.urlpath = urlpath
        
        userlist = api.request('meeting-usermanager-user-list',{'sco-id': room.sco_id},False)
        if userlist.status_code() == 'ok':
            room.user_count = int(userlist.et.xpath("count(.//userdetails)"))
            room.host_count = int(userlist.et.xpath("count(.//userdetails/role[text() = 'host'])"))
        
        room.save()
        room.unlock()
    else:
        room.unlock()
    
def _import_acc(acc):
    api = ac_api_client_direct(acc)
    backthen = datetime.now()-timedelta(seconds=6000000)
    backthen = backthen.replace(microsecond=0)
    logging.debug(backthen.isoformat())
    r = api.request('report-bulk-objects',{'filter-type': 'meeting','filter-gt-date-modified': backthen.isoformat()})
    for row in r.et.xpath("//row"):
        _import_one_room(acc,api,row)


@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def import_all_rooms():
    for acc in ACCluster.objects.all():
        _import_acc(acc)

def _import_meeting_room_session(api,acc,sco_id,row=None,room=None):
    try:
        if room == None:
            room = Room.objects.get(acc=acc,sco_id=sco_id)
        if row and row.findtext("date-end"):
            room.user_count = 0
            room.host_count = 0
        else:
            userlist = api.request('meeting-usermanager-user-list',{'sco-id': room.sco_id},False)
            if userlist.status_code() == 'ok':
                room.user_count = int(userlist.et.xpath("count(.//userdetails)"))
                room.host_count = int(userlist.et.xpath("count(.//userdetails/role[text() = 'host'])"))
            elif userlist.status_code() == 'no-access' and userlist.subcode() == 'not-available': #no active session
                room.user_count = 0
                room.host_count = 0
        room.save()
    except ObjectDoesNotExist:
        pass

def _import_meeting_sessions_acc(acc):
    api = ac_api_client_direct(acc)
    backthen = datetime.now()-timedelta(seconds=600000)
    backthen = backthen.replace(microsecond=0)
    logging.debug(backthen.isoformat())
    r = api.request('report-meeting-sessions',{'filter-gt-date-created': backthen.isoformat()})
    seen = {}
    for row in r.et.xpath("//row"):
        try:
            sco_id = int(row.get('sco-id'))
            _import_meeting_room_session(api,acc,sco_id,row,None)
            seen[sco_id] = True
        except Exception,ex:
            logging.error(ex)
   
    for room in Room.objects.filter(acc=acc,user_count=None):
        logging.debug("checking sessions on room: %s" % room)
        if seen.get(room.sco_id,False):
            continue
        try:
            logging.debug("importing sessions")
            _import_meeting_room_session(api,acc,room.sco_id,None,room)
        except Exception,ex:
            logging.error(ex)
            
def _recheck_active_meetings_acc(acc):
    api = ac_api_client_direct(acc)
    for room in Room.objects.filter(acc=acc,user_count__gt=0):
        _import_meeting_room_session(api,acc,room.sco_id,None,room)
        
@periodic_task(run_every=crontab(hour="*", minute="*/1", day_of_week="*"))
def _import_meeting_sessions():
    for acc in ACCluster.objects.all():
        _import_meeting_sessions_acc(acc)
        _recheck_active_meetings_acc(acc)