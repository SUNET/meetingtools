'''
Created on Jan 31, 2011

@author: leifj
'''

from django.db import models
from django.db.models.fields import CharField, BooleanField, IntegerField,\
    TextField
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.models import User
from meetingtools.apps.cluster.models import ACCluster
import time
import tagging
from meetingtools.settings import BASE_URL
from django.db.models.signals import post_save
from tagging.models import Tag

class Room(models.Model):
    creator = ForeignKey(User,editable=False)
    name = CharField(max_length=128,unique=True)
    urlpath = CharField(verbose_name="Custom URL",max_length=128,unique=True)
    acc =  ForeignKey(ACCluster,verbose_name="Adobe Connect Cluster",editable=False)
    self_cleaning = BooleanField(verbose_name="Clean-up when empty?")
    allow_host = BooleanField(verbose_name="Allow first participant to become host?",default=True)
    sco_id = IntegerField(verbose_name="Adobe Connect Room")
    source_sco_id = IntegerField(verbose_name="Template",blank=True,null=True)
    folder_sco_id = IntegerField(verbose_name="Adobe Connect Room Folder",editable=False)
    description = TextField(blank=True,null=True)
    user_count = IntegerField(verbose_name="User Count At Last Visit",editable=False,blank=True,null=True)
    host_count = IntegerField(verbose_name="Host Count At Last Visit",editable=False,blank=True,null=True)
    timecreated = models.DateTimeField(auto_now_add=True)
    lastupdated = models.DateTimeField(auto_now=True)
    lastvisited = models.DateTimeField(blank=True,null=True)
    
    class Meta:
        unique_together = ('acc','sco_id')
    
    def __unicode__(self):
        return "%s (sco_id=%s,source_sco_id=%s,folder_sco_id=%s,urlpath=%s)" % (self.name,self.sco_id,self.source_sco_id,self.folder_sco_id,self.urlpath)
    
    def lastvisit(self):
        if not self.lastvisited:
            return 0
        else:
            return int(time.mktime(self.lastvisited.timetuple())*1000)
        
    def go_url(self):
        return "%s/go/%s" % (BASE_URL,self.urlpath)
        
    def go_url_internal(self):
        return "%s/go/%d" % (BASE_URL,self.id)
    
    def permalink(self):
        return "%s/room/%d" % (BASE_URL,self.id)
    
    def recordings_url(self):
        return "%s/room/%d/recordings" % (BASE_URL,self.id)
        
    def nusers(self):
        if self.user_count == None:
            return "unknown many"
        else:
            return self.user_count
        
    def nhosts(self):
        if self.host_count == None:
            return "unknown many"
        else:
            return self.host_count
        
tagging.register(Room)

def _magic_tags(sender,**kwargs):
    room = kwargs['instance']
    if room.self_cleaning:
        Tag.objects.add_tag(room, "cleaning")
    else:
        tags = Tag.objects.get_for_object(room)
        ntags = []
        for tag in tags:
            if tag.name != "cleaning":
                ntags.append(tag.name)
        Tag.objects.update_tags(room, " ".join(ntags))
    
post_save.connect(_magic_tags,sender=Room)