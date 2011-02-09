'''
Created on Jan 31, 2011

@author: leifj
'''

from django.db import models
from django.db.models.fields import CharField, BooleanField, IntegerField, SmallIntegerField
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.models import User
from meetingtools.apps.cluster.models import ACCluster

class Room(models.Model):
    creator = ForeignKey(User,editable=False)
    name = CharField(max_length=128,blank=True,unique=True)
    urlpath = CharField(max_length=128,blank=True,unique=True)
    acc =  ForeignKey(ACCluster,verbose_name="Adobe Connect Cluster",editable=False)
    participants = CharField(max_length=255,blank=True,verbose_name="Participants") # populate from entitlement held by creator session
    presenters = CharField(max_length=255,blank=True,verbose_name="Presenters") # populate from entitlement held by creator session
    hosts = CharField(max_length=255,blank=True,verbose_name="Hosts") # populate from entitlement held by creator session
    self_cleaning = BooleanField(verbose_name="Clean-up when empty?")
    sco_id = IntegerField(verbose_name="Adobe Connect Room",blank=False)
    source_sco_id = IntegerField(verbose_name="Template",blank=True,null=True)
    timecreated = models.DateTimeField(auto_now_add=True)
    lastupdated = models.DateTimeField(auto_now=True)
    lastvisited = models.DateTimeField(blank=True,null=True)
    
    def __unicode__(self):
        return "%s (sco_id=%d,source_sco_id=%d)" % (self.name,self.sco_id,self.source_sco_id)
    