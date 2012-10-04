from meetingtools.ac.api import ACPClient
import time
from meetingtools.apps.cluster.models import acc_for_user
from django.core.cache import cache
from Queue import Queue
import logging
from django.contrib.auth.models import User

_pools = {}

MAXCALLS = 10    
MAXIDLE = 10

class ClientPool(object):
    
    def __init__(self,acc,maxsize=0,increment=2):
        self._q = Queue(maxsize)
        self._acc = acc
        self._increment = increment
    
    def allocate(self):
        now = time.time()
        api = None
        while not api:
            if self._q.empty():
                for i in range(1,self._increment):
                    logging.debug("adding instance %d" % i)
                    api = ACPClient(self._acc.api_url,self._acc.user,self._acc.password,cpool=self)
                    self._q.put_nowait(api)
            
            api = self._q.get()
            if api and (api.age > MAXCALLS or now - api.lastused > MAXIDLE):
                api = None
        return api

# with ac_api_client(acc) as api
#    ...

def ac_api_client(o):
    acc = o
    logging.debug("ac_api_client(%s)" % repr(o))
    if hasattr(o,'user') and isinstance(getattr(o,'user'),User):
        acc = acc_for_user(getattr(o,'user'))
    elif hasattr(o,'acc'):
        acc = getattr(o,'acc')
    
    tag = 'ac_api_client_%d' % acc.id
    pool = _pools.get(tag)
    if pool is None:
        pool = ClientPool(acc,maxsize=30)
        _pools[tag] = pool
        
    return pool.allocate()



    