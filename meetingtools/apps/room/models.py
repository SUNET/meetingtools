'''
Created on Jan 31, 2011

@author: leifj
'''

from django.db import models
from django.db.models.fields import CharField, BooleanField, URLField

class Room(models.Model):
    name = CharField(max_length=128)
    group = CharField(max_length=128) # populate from entitlement held by creator
    resetWhenEmpty = BooleanField()
    meetingRoomUrl = URLField()