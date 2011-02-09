import meetingtools.mimeparse as mimeparse
import re
import rfc822
from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseForbidden,\
    HttpResponseRedirect
from django.utils import simplejson
from django.template import loader
from meetingtools.settings import PREFIX_URL

default_suffix_mapping = {"\.htm(l?)$": "text/html",
                          "\.json$": "application/json",
                          "\.rss$": "application/rss+xml",
                          "\.torrent$": "application/x-bittorrent"}

def _accept_types(request, suffix):
    for r in suffix.keys():
        p = re.compile(r)
        if p.search(request.path):
            return suffix.get(r)
    return None


def timeAsrfc822 ( theTime ) :
    return rfc822 . formatdate ( rfc822 . mktime_tz ( rfc822 . parsedate_tz ( theTime . strftime ( "%a, %d %b %Y %H:%M:%S" ) ) ) )

def make_response_dict(request,d={}):
 
    if request.user.is_authenticated():
        d['user'] = request.user
        d['prefix'] = PREFIX_URL

    return d

def json_response(data):
    r = HttpResponse(simplejson.dumps(data),content_type='application/json')
    r['Cache-Control'] = 'no-cache, must-revalidate'
    r['Pragma'] = 'no-cache'
    
    return r

def render403(message="You don't seem to have enough rights for what you are trying to do....",dict={}):
    dict['message'] = message
    return HttpResponseForbidden(loader.render_to_string("403.html",dict))
    
def respond_to(request, template_mapping, dict={}, suffix_mapping=default_suffix_mapping):
    accept = _accept_types(request, suffix_mapping)
    if accept is None:
        accept = (request.META['HTTP_ACCEPT'].split(','))[0]
    content_type = mimeparse.best_match(template_mapping.keys(), accept)
    template = None
    if template_mapping.has_key(content_type):
        template = template_mapping[content_type]
    else:
        template = template_mapping["text/html"]
    if callable(template):
        response = template(make_response_dict(request,dict))
    elif isinstance(template, HttpResponse):
        response = template
        response['Content-Type'] = "%s; charset=%s" % (content_type, settings.DEFAULT_CHARSET)
    else:
        response = render_to_response(template,make_response_dict(request,dict))
        response['Content-Type'] = "%s; charset=%s" % (content_type, settings.DEFAULT_CHARSET)
    return response

def redirect_to(path):
    return HttpResponseRedirect("%s%s" % (PREFIX_URL,path))