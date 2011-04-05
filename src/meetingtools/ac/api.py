'''
Created on Jan 31, 2011

@author: leifj
'''

import httplib2
from urllib import quote
import logging
from pprint import pformat
import os
import tempfile
from lxml import etree
import pprint
from meetingtools.site_logging import logger
import lxml

class ACPException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return etree.tostring(self.value)

class ACPResult():
    
    def __init__(self,content):
        self.et = etree.fromstring(content)
        self.status = self.et.find('status')
        
    def is_error(self):
        return self.status_code() != 'ok'

    def status_code(self):
        return self.status.get('code')

    def exception(self):
        raise ACPException,self.status

    def get_principal(self):
        logger.debug(lxml.etree.tostring(self.et))
        return self.et.xpath('principal')[0]

def _enc(v):
        ev = v
        if isinstance(ev,str) or isinstance(ev,unicode):
            ev = ev.encode('iso-8859-1')
        return ev

class ACPClient():
    
    def __init__(self,url,username=None,password=None):
        self.url = url
        self.session = None
        if username and password:
            self.login(username,password)
    
    def request(self,method,p={},raise_error=False):
        url = self.url+"?"+"action=%s" % method
        if self.session:
            url = url + "&session=%s" % self.session
        
        u = []
        for (k,v) in p.items():
            if v:
                kv = "%s=%s" % (k,quote(str(v)))
                u.append(kv)
        url = url + "&" + "&".join(u)
    
        h = httplib2.Http(tempfile.gettempdir()+os.sep+".cache");
        logging.debug(url)
        resp, content = h.request(url, "GET")
        logging.debug(pformat(resp))
        logging.debug(pformat(content))
        if resp.status != 200:
            raise ACPException,resp.reason
        
        if resp.has_key('set-cookie'):
            cookie = resp['set-cookie']
            if cookie:
                avp = cookie.split(";")
                if len(avp) > 0:
                    av = avp[0].split('=')
                    self.session = av[1]
                    
        r = ACPResult(content)
        if r.is_error() and raise_error:
            raise r.exception()
        
        return r;
    
    def login(self,username,password):
        result = self.request('login',{'login':username,'password':password})
        if result.is_error():
            raise result.exception()
    
    def find_or_create_principal(self,key,value,type,dict):
        result = self.request('principal-list',{'filter-%s' % key: value,'filter-type': type}, True)
        principal = result.get_principal()
        if result.is_error():
            if result.status_code() != 'no_data':
                result.exception()
        elif not principal:
            dict['principal-id'] = principal.get('principal-id')
        
        update_result = self.request('principal-update',dict)
        rp = update_result.get_principal()
        if not rp:
            rp = principal
        return principal
    
    def find_builtin(self,type):
        result = self.request('principal-list', {'filter-type': type}, True)
        return result.get_principal()
    
    def find_group(self,name):
        result = self.request('principal-list',{'filter-name':name,'filter-type':'group'},True)
        return result.get_principal()
    
    def add_remove_member(self,principal_id,group_id,is_member):
        m = "0"
        if is_member:
            m = "1"
        self.request('group-membership-update',{'group-id': group_id, 'principal-id': principal_id,'is-member':m},True)
        
    def add_member(self,principal_id,group_id):
        return self.add_remove_member(principal_id, group_id, True)
    
    def remove_member(self,principal_id,group_id):
        return self.add_remove_member(principal_id, group_id, False)