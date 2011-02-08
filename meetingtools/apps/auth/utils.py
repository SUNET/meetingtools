'''
Created on Jul 7, 2010

@author: leifj
'''
from uuid import uuid4

def nonce():
    return uuid4().hex

def anonid():
    return uuid4().urn

def groups(request):
    groups = []
    if request.user.is_authenticated():
        if request.session and request.session.has_key('entitlement'):
            groups = groups + request.session['entitlement']
        
        if '@' in request.user.username:
            (local,domain) = request.user.username.split('@')
            groups.append(domain)
            for e in ('member','employee','student'):
                groups.append("%s@%s" % (e,domain))

    return groups