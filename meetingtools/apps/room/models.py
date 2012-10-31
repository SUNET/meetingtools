'''
Created on Jan 31, 2011

@author: leifj
'''

from django.db import models
from django.db.models.fields import CharField, BooleanField, IntegerField,\
    TextField
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.models import User
from meetingtools.apps.sco.models import ACObject, get_sco
import time
import tagging
from meetingtools.settings import LOCK_DIR
from django.db.models.signals import post_save
from tagging.models import Tag
import os

class FileLock(object):
    
    def __init__(self,obj):
        self.obj = obj
    
    def __get__(self):
        return os.access(LOCK_DIR+os.sep+self.obj.__class__+"_"+self.obj.id+".lock",os.F_OK)
    def __set__(self,value):
        if not isinstance(value,bool):
            raise AttributeError
        if value:
            f = open(LOCK_DIR+os.sep+self.obj.__class__+"_"+self.obj.id+".lock")
            f.close()
        else:
            os.remove(LOCK_DIR+os.sep+self.obj.__class__+"_"+self.obj.id+".lock")
    def __delete__(self):
        raise AttributeError

class RoomLockedException(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Room(models.Model):
    creator = ForeignKey(User,editable=False)
    name = CharField(max_length=128)
    sco = ForeignKey(ACObject,editable=False,null=True)
    folder_sco = ForeignKey(ACObject,null=True,related_name="folders")
    source_sco = ForeignKey(ACObject,null=True,related_name="sources")
    deleted_sco = ForeignKey(ACObject,null=True,related_name="deleted")
    urlpath = CharField(verbose_name="Custom URL",max_length=128)
    self_cleaning = BooleanField(verbose_name="Clean-up when empty?")
    allow_host = BooleanField(verbose_name="Allow first participant to become host?",default=True)
    description = TextField(blank=True,null=True)
    user_count = IntegerField(verbose_name="User Count At Last Visit",editable=False,blank=True,null=True)
    host_count = IntegerField(verbose_name="Host Count At Last Visit",editable=False,blank=True,null=True)
    timecreated = models.DateTimeField(auto_now_add=True)
    lastupdated = models.DateTimeField(auto_now=True)
    lastvisited = models.DateTimeField(blank=True,null=True)
    
    class Meta:
        unique_together = (('name','folder_sco'))

    def __unicode__(self):
        return "%s (sco_id=%s,source_sco_id=%s,folder_sco_id=%s,urlpath=%s)" % \
               (self.name,self.sco.sco_id,self.source_sco.sco_id,self.folder_sco.sco_id,self.urlpath)

    @staticmethod
    def by_sco(sco):
        return Room.objects.get(sco=sco)

    @staticmethod
    def by_id(acc,sco_id):
        return Room.by_sco(get_sco(acc,sco_id))

    @staticmethod
    def by_name(acc,name):
        Room.objects.get(sco__acc=acc,name=name)

    def _lockf(self):
        return "%s%sroom-%d.lock" % (LOCK_DIR,os.sep,+self.id)
    
    def lock(self,msg=None):
        f = open(self._lockf(),'w')
        if msg:
            f.write(msg)
        f.close()
    
    def trylock(self,raise_on_locked=True):
        if self.is_locked():
            if raise_on_locked:
                raise RoomLockedException,"room %s is locked" % self.__unicode__()
            else:
                return False
        self.lock() #race!! - must use flock
        return True
        
    def unlock(self):
        os.remove(self._lockf())
        
    def is_locked(self):
        os.access(self._lockf(),os.F_OK)
    
    def lastvisit(self):
        if not self.lastvisited:
            return 0
        else:
            return int(time.mktime(self.lastvisited.timetuple())*1000)
        
    def lastupdate(self):
        if not self.lastupdated:
            return 0
        else:
            return int(time.mktime(self.lastupdated.timetuple()))
        
    def go_url(self):
        return "/go/%s" % self.urlpath
        
    def go_url_internal(self):
        return "/go/%d" % self.id
    
    def permalink(self):
        return "/room/%d" % self.id
    
    def recordings_url(self):
        return "/room/%d/recordings" % self.id
        
    def nusers(self):
        if self.user_count is None:
            return "unknown many"
        else:
            return self.user_count
        
    def nhosts(self):
        if self.host_count is None:
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