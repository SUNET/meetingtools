'''
Created on Jan 18, 2012

@author: leifj
'''
from pprint import pformat
from celery.task import periodic_task,task
from celery.schedules import crontab
from meetingtools.apps.sco.models import get_sco
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
from django.conf import settings
from django.core.mail import send_mail


def _owner_username(api,acc,sco):
    logging.debug(sco)
    key = 'ac:owner:%s/%s' % (acc,sco.get('sco-id'))
    logging.debug(key)
    try:
        name = cache.get(key)
        if name is None:
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
            if parent:
                logging.debug("parent: %s" % parent)
                if parent.findtext('name') == 'User Meetings':
                    name = sco.findtext('name')
                else:
                    name = _owner_username(api,acc,parent)

                if name is not None:
                    cache.set(key,name,30)
                
        return name
    except Exception,e:
        logging.debug(e)
        return None

def _extended_info(api,acc,sco_id):
    r = api.request('sco-info',{'sco-id':sco_id},False)
    if r.status_code == 'no-data':
        return None
    return r.et,_owner_username(api,acc,r.et.xpath('//sco')[0])
    
def _import_one_room(acc,api,row):
    sco_id = int(row.get('sco-id'))
    last = iso8601.parse_date(row.findtext("date-modified[0]"))
    room = None
    
    try:
        room = Room.objects.get(deleted_sco__acc=acc,deleted_sco__sco_id=sco_id)
        if room is not None:
            return # We hit a room in the process of being cleaned - let it simmer until next pass
    except ObjectDoesNotExist:
        pass
    except Exception,e:
        logging.debug(e)
        return
    
    try:
        logging.debug("finding acc=%s,sco_id=%d in our DB" % (acc,sco_id))
        room = Room.objects.get(sco__acc=acc,sco__sco_id=sco_id)
        if room.deleted_sco_id is not None:
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
        (r, username) = _extended_info(api, acc, sco_id)
        logging.debug("found room owned by %s. Time for an update" % username)
        if username is None:
            logging.warning("username not found for sco-id=%s while importing" % sco_id)
            return

        def _ft(t,exprs):
            for e in exprs:
                v = t.findtext(e)
                if v is not None:
                    return v
            return None

        logging.debug(etree.tostring(row))
        logging.debug(etree.tostring(r))
        urlpath = _ft(row, ["url[0]", "url-path[0]"]).strip("/")

        name = row.findtext('name[0]')
        description = row.findtext('description[0]')
        date_created = None
        try:
            date_created = iso8601.parse_date(row.findtext("date-created[0]"))
        except Exception:
            pass
        folder_sco_id = 0
        source_sco_id = 0

        def _ior0(elt,a,dflt):
            str = elt.get(a,None)
            if str is None or not str:
                return dflt
            else:
                return int(str)

        for elt in r.findall(".//sco[0]"):
            folder_sco_id = _ior0(elt,'folder-id',0)
            source_sco_id = _ior0(elt,'source-sco-id',0)

        logging.debug("urlpath=%s, name=%s, folder_sco_id=%s, source_sco_id=%s" % (urlpath,name,folder_sco_id,source_sco_id))

        if room is None:
            if folder_sco_id:
                user, created = User.objects.get_or_create(username=username)
                if created:
                    user.set_unusable_password()
                room = Room.objects.create(sco=get_sco(acc,sco_id),
                                        creator=user,name=name,
                                        description=description,
                                        folder_sco=get_sco(acc,folder_sco_id),
                                        source_sco=get_sco(acc,source_sco_id),
                                        urlpath=urlpath)
                room.trylock()
        else:
            if folder_sco_id:
                room.folder_sco = get_sco(acc,folder_sco_id)
            room.source_sco = get_sco(acc,source_sco_id)
            room.description = description
            room.urlpath = urlpath
            if date_created is not None:
                room.timecreated = date_created

        if room is not None:
            room.save()
            room.unlock()
    else:
        if room is not None:
            room.unlock()


def _user_meeting_folder(user,api):
    userid = user.username
    folders = api.request('sco-search-by-field',
                          {'filter-type': 'folder', 'field': 'name', 'query': userid}).et.xpath('//sco[folder-name="User Meetings"]')
    logging.debug("user meetings folder: "+pformat(folders))
    #folder = next((f for f in folders if f.findtext('.//folder-name') == 'User Meetings'), None)
    return folders[0].get('sco-id')


def import_user_rooms(acc, api, user):
    mf_sco_id = _user_meeting_folder(user, api)
    if mf_sco_id > 0:
        r = api.request('sco-contents', {'filter-type': 'meeting', 'sco-id': mf_sco_id})
        nr = 0
        ne = 0
        for row in r.et.xpath("//sco"):
            try:
                _import_one_room(acc, api, row)
                nr += 1
            except Exception, ex:
                logging.error(ex)
                ne += 1

        logging.info("%s: Imported %d rooms and got %d errors" % (acc, nr, ne))
    else:
        logging.warning("No user meetings folder found for %s" % user.username)

def import_acc(acc,since=0):
    with ac_api_client(acc) as api:
        r = None
        if since > 0:
            then = datetime.now()-timedelta(seconds=since)
            then = then.replace(microsecond=0)
            r = api.request('report-bulk-objects',{'filter-type': 'meeting','filter-gt-date-modified': then.isoformat()})
        else:
            r = api.request('report-bulk-objects',{'filter-type': 'meeting'})

        nr = 0
        ne = 0
        for row in r.et.xpath("//row"):
            try:
                _import_one_room(acc,api,row)
                nr += 1
            except Exception,ex:
                logging.error(ex)
                ne += 1

        logging.info("%s: Imported %d rooms and got %d errors" % (acc,nr,ne))

@periodic_task(run_every=crontab(hour="*", minute="*/15", day_of_week="*"))
def import_all_rooms():
    for acc in ACCluster.objects.all():
        import_acc(acc,since=3700)


def start_user_counts_poll(room,niter):
    poll_user_counts.apply_async(args=[room],kwargs={'niter': niter})

@task(name='meetingtools.apps.room.tasks.poll_user_counts',rate_limit="10/s")
def poll_user_counts(room,niter=0):
    logging.debug("polling user_counts for room %s" % room.name)
    with ac_api_client(room.sco.acc) as api:
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
            nr = 0
            then = datetime.now()-timedelta(seconds=600)
            for room in Room.objects.filter((Q(lastupdated__gt=then) | Q(lastvisited__gt=then)) & Q(sco__acc=acc)):
                api.poll_user_counts(room)
                nr += 1
            logging.info("%s: Checked usage for %d rooms since %s" % (acc,nr,then))

# look for sessions that are newer than the one we know about for a room
@periodic_task(run_every=crontab(hour="*/3", minute="0", day_of_week="*"))
def import_sessions():
    for room in Room.objects.all():
        with ac_api_client(room.sco.acc) as api:
            p = {'sco-id': room.sco.sco_id,'sort-date-created': 'asc'}
            if room.lastvisited is not None:
                last = room.lastvisited
                last.replace(microsecond=0)
                p['filter-gt-date-created'] = last.isoformat()
            r = api.request('report-meeting-sessions',p)
            for row in r.et.xpath("//row"):
                date_created = iso8601.parse_date(row.findtext("date-created"))
                logging.debug("sco_id=%d lastvisited: %s" % (room.sco.sco_id,date_created))
                room.lastvisited = date_created
                room.save()
                break

@periodic_task(run_every=crontab(hour="*", minute="*/15", day_of_week="*"))
def import_transactions():
    for acc in ACCluster.objects.all():
        then = datetime.now() - timedelta(seconds=1200)
        then = then.replace(microsecond=0)
        with ac_api_client(acc) as api:
            seen = {}
            r = api.request('report-bulk-consolidated-transactions',
                            {'filter-type': 'meeting', 'sort-date-created': 'asc',
                             'filter-gt-date-created': then.isoformat()})
            for row in r.et.xpath("//row"):
                sco_id = row.get('sco-id')
                logging.debug("last session for sco_id=%s" % sco_id)
                if not seen.get(sco_id,False): #pick the first session for each room - ie the one last created
                    seen[sco_id] = True
                    try:
                        room = Room.objects.get(sco__acc=acc,sco__sco_id=sco_id)
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
            send_mail(subject,message,settings.NOREPLY,[p.email])
        else:
            logging.info("User %s has no email address - email not sent" % user.username)
    except ObjectDoesNotExist:
        logging.info("User %s has no profile - email not sent" % user.username)
    except Exception,exc:
        logging.error("Error while sending email: \n%s" % exc)
        send_message.retry(exc=exc)
                
#@periodic_task(run_every=crontab(hour="1", minute="5", day_of_week="*"))
def clean_old_rooms():
    for acc in ACCluster.objects.all():
        then = datetime.now() - timedelta(days=30)
        then = then.replace(microsecond=0)
        with ac_api_client(acc) as api:
            for room in Room.objects.filter(lastvisited__lt=then):
                logging.debug("room %s was last used %s" % (room.name,humanize.naturalday(room.lastvisited)))
                send_message.apply_async([room.creator,"You have an unused meetingroom at %s" % acc.name ,"Do you still need %s (%s)?" % (room.name,room.permalink())])