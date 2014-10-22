from meetingtools import context_processors
import meetingtools.mimeparse as mimeparse
import re
import csv
import codecs
import cStringIO
import rfc822
from django.conf import settings
from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseForbidden,\
    HttpResponseRedirect
from django.utils import simplejson
from django.template import loader, RequestContext

default_suffix_mapping = {"\.htm(l?)$": "text/html",
                          "\.json$": "application/json",
                          "\.rss$": "application/rss+xml",
                          "\.atom$": "application/atom+xml",
                          "\.torrent$": "application/x-bittorrent"}


class UnicodeCSVWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def _accept_types(request, suffix):
    for r in suffix.keys():
        p = re.compile(r)
        if p.search(request.path):
            return suffix.get(r)
    return None


def timeAsrfc822 ( theTime ) :
    return rfc822 . formatdate ( rfc822 . mktime_tz ( rfc822 . parsedate_tz ( theTime . strftime ( "%a, %d %b %Y %H:%M:%S" ) ) ) )

def make_response_dict(request,d=dict()):
    if request.user.is_authenticated():
        d['user'] = request.user

    ctx = RequestContext(request,d,[context_processors.theme,context_processors.misc_urls,context_processors.request])
    print repr(ctx['theme'])
    return ctx

def json_response(data,request=None):
    response_data = None
    if request and request.GET.has_key('callback'):
        callback = request.GET['callback']
        json = simplejson.dumps(data)
        response_data = "%s(%s)" % (callback, json)
    else:
        response_data = simplejson.dumps(data)
    r = HttpResponse(response_data,content_type='application/json')
    r['Cache-Control'] = 'no-cache, must-revalidate'
    r['Pragma'] = 'no-cache'
    return r


def dicts_to_csv_response(dict_list, header=None):
    """
    Takes a list of dicts and returns a comma separated file with all dict keys
    and their values.
    """
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=result.csv; charset=utf-8;'
    writer = UnicodeCSVWriter(response, delimiter=',', quoting=csv.QUOTE_NONNUMERIC)
    if not header:
        key_set = set()
        for item in dict_list:
            key_set.update(item.keys())
        key_set = sorted(key_set)
    else:
        key_set = header
    writer.writerow(key_set)  # Line collection with header
    for item in dict_list:
        line = []
        for key in key_set:
            try:
                line.append('%s' % item[key])
            except KeyError:
                line.append('')  # Node did not have that key, add a blank item.
        writer.writerow(line)
    return response


def render500(request):
    return render_to_response("500.html",RequestContext(request,{},[context_processors.misc_urls]))

def render403(message="You don't seem to have enough rights for what you are trying to do....",dict=dict()):
    dict['message'] = message
    return HttpResponseForbidden(loader.render_to_string("403.html",dict))
    
def respond_to(request, template_mapping, dict=dict(), suffix_mapping=default_suffix_mapping):
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
    return HttpResponseRedirect(path)