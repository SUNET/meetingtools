'''
Created on Jan 18, 2012

@author: leifj
'''
from celery.task import periodic_task,task
from celery.schedules import crontab
from meetingtools.apps.cluster.models import ACCluster
from meetingtools.ac import ac_api_client
from meetingtools.apps.room.models import Room
import iso8601
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
import logging
from datetime import datetime,timedelta
from lxml import etree
from django.db.models import Q
from django.contrib.humanize.templatetags import humanize
from meetingtools.apps.userprofile.models import profile
from django.core.mail import send_mail
from meetingtools.settings import NOREPLY, BASE_URL

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
    
    #logging.debug("last %s" % last)
    #logging.debug("lastupdated %s" % lastupdated)
    if not room or lastupdated < last:
        (r,username) = _extended_info(api, sco_id)
        logging.debug("found room owned by %s time for and update" % username)
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

        room.save()
        room.unlock()
    else:
        room.unlock()
    
def _import_acc(acc):
    with ac_api_client(acc) as api:
        then = datetime.now()-timedelta(seconds=3600)
        then = then.replace(microsecond=0)
        r = api.request('report-bulk-objects',{'filter-type': 'meeting','filter-gt-date-modified': then.isoformat()})
        for row in r.et.xpath("//row"):
            _import_one_room(acc,api,row)

@periodic_task(run_every=crontab(hour="*", minute="*/5", day_of_week="*"))
def import_all_rooms():
    for acc in ACCluster.objects.all():
        _import_acc(acc)
  
def start_user_counts_poll(room,niter):
    poll_user_counts.apply_async(args=[room],kwargs={'niter': niter})
  
@task(name='meetingtools.apps.room.tasks.poll_user_counts',rate_limit="10/s")
def poll_user_counts(room,niter=0):
    logging.debug("polling user_counts for room %s" % room.name)
    with ac_api_client(room.acc) as api:
        (nusers,nhosts) = api.poll_user_counts(room)
        if nusers > 0:
            logging.debug("room occupied by %d users and %d hosts, checking again in 20 ..." % (nusers,nhosts))
            poll_user_counts.apply_async(args=[room],kwargs={'niter': 0},countdown=20)
        elif niter > 0:
            logging.debug("room empty, will check again in 5 for %d more times ..." % (niter -1))
            poll_user_counts.apply_async(args=[room],kwargs={'niter': niter-1},countdown=5)
        return (nusers,nhosts)
    
# belts and suspenders - we setup polling for active rooms aswell...      
@periodic_task(run_every=crontab(hour="*", minute="*/5", day_of_week="*"))
def import_recent_user_counts():
    for acc in ACCluster.objects.all():
        with ac_api_client(acc) as api:
            then = datetime.now()-timedelta(seconds=600)
            for room in Room.objects.filter((Q(lastupdated__gt=then) | Q(lastvisited__gt=then)) & Q(acc=acc)):
                api.poll_user_counts(room)
        
# look for sessions that are newer than the one we know about for a room
@periodic_task(run_every=crontab(hour="*", minute="*", day_of_week="*"))
def import_sessions():
    for room in Room.objects.all():
        with ac_api_client(room.acc) as api:
            p = {'sco-id': room.sco_id,'sort-date-created': 'asc'}
            if room.lastvisited != None:
                last = room.lastvisited
                last.replace(microsecond=0)
                p['filter-gt-date-created'] = last.isoformat()
            r = api.request('report-meeting-sessions',p)
            for row in r.et.xpath("//row"):
                date_created = iso8601.parse_date(row.findtext("date-created"))
                logging.debug("sco_id=%d lastvisited: %s" % (room.sco_id,date_created))
                room.lastvisited = date_created
                room.save()
                break

#@periodic_task(run_every=crontab(hour="*", minutes="*/5", day_of_week="*"))
def import_transactions():
    for acc in ACCluster.objects.all():
        then = datetime.now() - timedelta(seconds=600)
        then = then.replace(microsecond=0)
        with ac_api_client(acc) as api:
            seen = {}
            r  = api.request('report-bulk-consolidated-transactions',{'filter-type':'meeting','sort-date-created': 'asc','filter-gt-date-created': then.isformat()})
            for row in r.et.xpath("//row"):
                sco_id = row.get('sco-id')
                logging.debug("last session for sco_id=%d" % sco_id)
                if not seen.get(sco_id,False): #pick the first session for each room - ie the one last created
                    seen[sco_id] = True
                    try:
                        room = Room.objects.get(acc=acc,sco_id=sco_id)
                        date_created = iso8601.parse_date(row.findtext("date-created"))
                        room.lastvisited = date_created
                        room.save()
                    except ObjectDoesNotExist:
                        pass # we only care about rooms we know about here
                
@task(name="meetingtools.apps.room.tasks.mail")
def send_message(user,subject,message):
    try:
        p = user.get_profile()
        if p and p.email:
            send_mail(subject,message,NOREPLY,[p.email])
        else:
            logging.info("User %s has no email address - email not sent" % user.username)
    except ObjectDoesNotExist:
        logging.info("User %s has no profile - email not sent" % user.username)
    except Exception,exc:
        logging.error("Error while sending email: \n%s" % exc)
        send_message.retry(exc=exc)
                
@periodic_task(run_every=crontab(hour="1", minute="5", day_of_week="*"))
def clean_old_rooms():
    for acc in ACCluster.objects.all():
        then = datetime.now() - timedelta(days=30)
        then = then.replace(microsecond=0)
        with ac_api_client(acc) as api:
            for room in Room.objects.filter(lastvisited__lt=then):
                logging.debug("room %s was last used %s" % (room.name,humanize.naturalday(room.lastvisited)))
                send_message.apply_async([room.creator,"You have an unused meetingroom at %s" % BASE_URL,"Do you still need %s (%s)?" % (room.name,room.permalink())])