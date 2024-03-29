'''
Created on Feb 4, 2011

@author: leifj
'''

def session(request,key=None,val=None):
    if key:
        if val:
            request.session[key] = val
            return val
        else:
            if not request.session.has_key(key):
                request.session[key] = None
            return request.session[key]
    else:
        return request.session

def base_url(request,path="/"):
    return "%s://%s%s" % ({True: 'https',False:'http'}[request.is_secure()],request.get_host(),path)