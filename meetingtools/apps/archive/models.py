from datetime import datetime
from iso8601 import iso8601
from tagging.models import Tag
from meetingtools.ac import ac_api_client
from meetingtools.apps.room.models import Room
from meetingtools.apps.sco.models import ACObject, get_sco, sco_mkdir

__author__ = 'leifj'

from django.db import models
from django.db.models import ForeignKey, TextField, CharField

class Archive(models.Model):
    sco = ForeignKey(ACObject,editable=False,unique=True)
    folder_sco = ForeignKey(ACObject,editable=False,related_name='archive_folder')
    room = ForeignKey(Room,editable=False,related_name='archives')
    description = TextField(blank=True,null=True)
    name = CharField(max_length=128,blank=True,null=True)
    urlpath = CharField(max_length=128)
    timecreated = models.DateTimeField(auto_now_add=True)
    lastupdated = models.DateTimeField(auto_now=True)

    def __unicode__(self):
        return "archive %s, sco %s, in folder %s" % (self.name,self.sco,self.folder_sco)

def publish_archive(room,sco_id,tags=None):
    acc = room.sco.acc
    sco = get_sco(acc,sco_id)

    info = sco.info(True)
    dt = info['timecreated']
    folder_sco = sco_mkdir(acc,"content/%d/%s/%s" % (dt.year,dt.month,dt.day))
    with ac_api_client(acc) as api:
        ar,create = Archive.objects.get_or_create(sco=sco,folder_sco=folder_sco,room=room)
        ar.timecreated=info['timecreated']
        if info['description']:
            ar.description = info['description']
        if info['name']:
            ar.name = info['name']
        ar.save()
        try:
            r = api.request('sco-move',{'sco-id':sco_id,'folder-id':folder_sco.sco_id},True)
            r = api.request('permissions-update',{'acl-id':sco_id,'permission-id': 'view','principal-id':'public-access'})
        except Exception,ex:
            ar.delete()
            raise ex

    if tags is not None:
        Tag.objects.update_tags(ar, ' '.join(tags))

    return ar