'''
Created on Feb 3, 2011

@author: leifj
'''

from django.db import models
from django.db.models.fields import CharField, URLField, TextField

class ACCluster(models.Model):
    api_url = URLField()
    url = URLField()
    user = CharField(max_length=128)
    password = CharField(max_length=128)
    name = CharField(max_length=128,blank=True,unique=True)
    domain_match = TextField()
    
    def __unicode__(self):
        return self.url
    
    def make_url(self,path=""):
        return "%s%s" % (self.url,path)