"""
Abstract sco objects and utility methods
"""
import logging

__author__ = 'leifj'

from meetingtools.ac import ac_api_client
from meetingtools.apps.cluster.models import ACCluster
from django.db import models
from django.db.models import fields, ForeignKey
from django.core.cache import cache
from datetime import datetime
from iso8601 import iso8601

class ACObject(models.Model):
    acc = ForeignKey(ACCluster,editable=False)
    sco_id = fields.IntegerField()
    is_deleted = fields.BooleanField(default=False,editable=False)
    timecreated = models.DateTimeField(auto_now_add=True)
    lastupdated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('acc','sco_id')

    def __unicode__(self):
        return "%s#%d" % (self.acc,self.sco_id)

    def info(self,raise_errors=False):
        with ac_api_client(self.acc) as api:
            r = api.request('sco-info',{'sco-id':self.sco_id},raise_errors)
            if r.status_code == 'no-data':
                if raise_errors:
                    raise ValueError("No data about %s" % self)
                else:
                    return None

            d = dict()
            for sco_elt in r.et.findall(".//sco"): #only one but this degrades nicely
                dt = datetime.now() # a fallback just in case
                dt_text = sco_elt.findtext('date-created')
                if dt_text is not None and len(dt_text) > 0:
                    dt = iso8601.parse_date(sco_elt.findtext('date-created'))
                    d['timecreated']=dt
                for a in ('description','name','url-path'):
                    v = sco_elt.findtext(a)
                    if v is not None:
                        d[a] = v
            return d

def get_sco(acc,sco_id):
    key = "ac:sco:%s/%s" % (acc,sco_id)
    sco = cache.get(key)
    if sco is None:
        sco,created = ACObject.objects.get_or_create(acc=acc,sco_id=sco_id)
        assert sco is not None
        cache.set(key,sco,30)
    return sco

def get_sco_shortcuts(acc,shortcut_id):
    key = "ac:shortcuts:%s" % acc
    shortcuts = cache.get(key)
    if not shortcuts:
        shortcuts = {}
        with ac_api_client(acc) as api:
            r = api.request('sco-shortcuts')
            for sco_elt in r.et.findall(".//sco"):
                shortcuts[sco_elt.get('type')] = get_sco(acc,sco_elt.get('sco-id'))
        cache.set(key,shortcuts)
    return shortcuts.get(shortcut_id,None)

def _mkdir(api,folder_sco_id,name):
    r = api.request('sco-update',{'name':name,'folder-id':folder_sco_id,'type':'folder'},True)
    sco_elt = r.et.find(".//sco")
    assert(sco_elt is not None)
    sco_id = sco_elt.get('sco-id')
    assert sco_id > 0
    return sco_id

def _isdir(api,folder_sco_id,name):
    r = api.request('sco-contents',{'sco-id':folder_sco_id,'filter-type':'folder','filter-name':name},True)
    sco_elt = r.et.find(".//sco")
    if sco_elt is None:
        return None
    return sco_elt.get('sco-id')

def sco_mkdir(acc,path):
    p = path.split("/")
    p0 = p.pop(0)
    folder_sco = get_sco_shortcuts(acc,p0) #note that first part of path must be the @type of the tree, not the name
    assert folder_sco is not None,ValueError("Unable to find shortcut '%s" % p0)
    folder_sco_id = folder_sco.sco_id
    with ac_api_client(acc) as api:
        for n in p:
            sco_id = _isdir(api,folder_sco_id,n)
            if sco_id is None:
                sco_id = _mkdir(api,folder_sco_id,n)
            folder_sco_id = sco_id
    return get_sco(acc,folder_sco_id)