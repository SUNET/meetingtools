from meetingtools.ac.api import ACPClient
import time
from meetingtools.apps.cluster.models import acc_for_user

def ac_api_client_cache(request,acc=None):
    if acc == None:
        acc = acc_for_user(request.user)
    tag = 'ac_api_client_%s' % acc.name
    if not request.session.has_key(tag):
        request.session[tag] = ACPClientWrapper(acc)
        
    return request.session[tag]

def ac_api_client_nocache(request,acc=None):
    if acc == None:
        acc = acc_for_user(request.user)
    return ACPClientWrapper(acc)

def ac_api_client_direct(acc):
    return ACPClientWrapper(acc)

ac_api_client = ac_api_client_cache

def ac_api(request,acc=None):
    return ACPClient(acc.api_url,acc.user,acc.password)

MAXCALLS = 10    
MAXIDLE = 10

class ACPClientWrapper(object):
    
    def __init__(self,acc):
        self.acc = acc
        self._delegate = None
        self.ncalls = 0
        self.lastcall = time.time()
        
    def invalidate(self):
        self._delegate = None
        
    def client_factory(self):
        now = time.time()
        if self.ncalls > MAXCALLS or now - self.lastcall > MAXIDLE or not self._delegate:
            self._delegate = ACPClient(self.acc.api_url,self.acc.user,self.acc.password)
            self.ncalls = 0
        self.ncalls += 1
        self.lastcall = now
        return self._delegate
        
    def __getattr__(self,name):
        client = self.client_factory()
        return getattr(client,name)
    