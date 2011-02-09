from meetingtools.ac.api import ACPClient

def ac_api_client_cached(request,acc):
    tag = 'ac_api_client_%s' % acc.name
    if not request.session.has_key(tag):
        request.session[tag] = ACPClient(acc.api_url,acc.user,acc.password)
        
    return request.session[tag]

def ac_api_client(request,acc):
    return ACPClient(acc.api_url,acc.user,acc.password)
    