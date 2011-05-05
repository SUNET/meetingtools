'''
Created on Jan 31, 2011

@author: leifj
'''

from django.db import models
from django.db.models.fields import CharField, BooleanField, IntegerField
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.models import User
from meetingtools.apps.cluster.models import ACCluster
import time
from django_co_acls.models import AccessControlEntry

class Room(models.Model):
    creator = ForeignKey(User,editable=False)
    name = CharField(max_length=128,unique=True)
    urlpath = CharField(verbose_name="Custom URL",max_length=128,unique=True)
    acc =  ForeignKey(ACCluster,verbose_name="Adobe Connect Cluster",editable=False)
    self_cleaning = BooleanField(verbose_name="Clean-up when empty?")
    sco_id = IntegerField(verbose_name="Adobe Connect Room")
    source_sco_id = IntegerField(verbose_name="Template",blank=True,null=True)
    folder_sco_id = IntegerField(verbose_name="Adobe Connect Room Folder",editable=False)
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