'''
Created on Jan 31, 2011

@author: leifj
'''

from lxml import etree
import httplib2
from urllib import urlencode

class ACPException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)

class ACPResult():
    
    def __init__(self,content):
        self.et = etree.parse(content)
        self.status = self.et.find('status')
        
    def is_error(self):
        return self.status.get('code') != 'ok'

    def exception(self):
        raise ACPException,self.status

    def get_principal(self):
        return self.et.find('principal')

class ACPClient():
    
    def __init__(self,url,username=None,password=None):
        self.url = url
        self.session = None
        if username and password:
            self.login(username,password)
        
    def request(self,method,p={}):
        url = self.url+"?"+"action=%s" % method
        if self.session:
            url = url + "&session=%s" % self.session
        urlencode(dict([k,v.encode("iso-8859-1")] for (k,v) in p.items()))
    
        h = httplib2.Http(".cache");
        resp, content = h.request(url, "GET")
        if resp.status != 200:
            raise ACPException,resp.reason
        
        if resp.has_key('set-cookie'):
            cookie = resp['set-cookie']
            if cookie:
                avp = cookie.split(";")
                if avp.len > 0:
                    av = avp[0].split('=')
                    self.session = av[1]
                    
        return ACPResult(content)
    
    def login(self,username,password):
        result = self.request('login',{'login':username,'password':password})
        if result.is_error():
            raise result.exception()
    