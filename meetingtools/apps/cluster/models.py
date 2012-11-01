'''
Created on Feb 3, 2011

@author: leifj
'''

from django.db import models
from django.db.models.fields import CharField, URLField, TextField, IntegerField, BooleanField
import re

class ACCluster(models.Model):
    api_url = URLField()
    url = URLField()
    user = CharField(max_length=128)
    password = CharField(max_length=128)
    name = CharField(max_length=128,blank=True,unique=True)
    default_template_sco_id = IntegerField(blank=True,unique=True)
    domain_match = TextField()
    cross_domain_sso = BooleanField(default=True)

    def __unicode__(self):
        return self.url

    def make_url(self,path=""):
        return "%s%s" % (self.url,path)

    def make_dl_url(self,path=""):
        return "%s%s/output/%s.zip?download=zip" % (self,path.strip("/"),path.strip("/"))

def acc_for_user(user):
    (local,domain) = user.username.split('@')
    if not domain:
        #raise Exception,"Improperly formatted user: %s" % user.username
        domain = "nordu.net" # testing with local accts only
    for acc in ACCluster.objects.all():
        for regex in acc.domain_match.split():
            if re.match(regex.strip(),domain):
                return acc
    raise Exception,"I don't know which cluster you belong to... (%s)" % user.username
