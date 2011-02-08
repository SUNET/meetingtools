'''
Created on Jul 5, 2010

@author: leifj
'''
from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.ForeignKey(User,blank=True,related_name='profile')
    display_name = models.CharField(max_length=255,blank=True)
    email = models.EmailField(blank=True)
    idp = models.CharField(max_length=255)
    timecreated = models.DateTimeField(auto_now_add=True)
    lastupdated = models.DateTimeField(auto_now=True)
    
    def __unicode__(self):
        return "%s - %s" % (self.user.username,self.display_name)

def profile(user):
    return UserProfile.objects.get(user=user)
