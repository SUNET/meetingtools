'''
Created on Jan 31, 2011

@author: leifj
'''
from StringIO import StringIO
import hashlib
from django.core.cache import get_cache
import httplib2
from urllib import quote_plus
import logging
from pprint import pformat
import os
import tempfile
import time
from lxml import etree
from meetingtools.site_logging import logger
import lxml
from django.http import HttpResponseRedirect
from celery.execute import send_task


class ACPException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return etree.tostring(self.value)


def _first_or_none(x):
    if not x:
        return None
    return x[0]


def strip_control_characters(input):
    if input:
        import re

        # unicode invalid characters
        RE_XML_ILLEGAL = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])' + \
                         u'|' + \
                         u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
                         (unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                          unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                          unichr(0xd800), unichr(0xdbff), unichr(0xdc00), unichr(0xdfff),
                         )
        input = re.sub(RE_XML_ILLEGAL, "", input)

        # ascii control characters
        input = re.sub(r"[\x01-\x1F\x7F]", "", input)

    return input


class ACPResult():
    def __init__(self, content):
        self.et = etree.fromstring(strip_control_characters(content))
        self.status = _first_or_none(self.et.xpath('//status'))

    def is_error(self):
        return self.status_code() != 'ok'

    def status_code(self):
        return self.status.get('code')

    def subcode(self):
        return self.status.get('subcode')

    def exception(self):
        raise ACPException, self.status

    def get_principal(self):
        logger.debug(lxml.etree.tostring(self.et))
        return _first_or_none(self.et.xpath('//principal'))

    def pretty_print(self):
        return lxml.etree.tostring(self.et, pretty_print=True)


def _enc(v):
    ev = v
    if isinstance(ev, str) or isinstance(ev, unicode):
        ev = ev.encode('iso-8859-1')
    return ev


def _getset(d, key, value=None):
    if value:
        if d.has_key(key):
            return d[key]
        else:
            return None
    else:
        d[key] = value


class ACPClient():
    def __init__(self, url, username=None, password=None, cache=True, cpool=None):
        self._cpool = cpool
        self.age = 0
        self.createtime = time.time()
        self.lastused = self.createtime
        self.url = url
        self.session = None
        if username and password:
            self.login(username, password)
        if cache:
            self._cache = {'login': {}, 'group': {}}

    def __exit__(self, type, value, traceback):
        if self._cpool and not value:
            self._cpool._q.put_nowait(self)

    def __enter__(self):
        return self

    class CacheWrapper():

        def __init__(self, cache):
            self._cache = cache

        def _shorten(self, key):
            h = hashlib.sha1()
            h.update(key)
            return h.hexdigest()

        def add(self, key, value, timeout=0):
            return self._cache.add(self._shorten(key), value)

        def get(self, key, default=None):
            return self._cache.get(self._shorten(key), default)

        def set(self, key, value, timeout=0):
            return self._cache.set(self._shorten(key), value)

    def request(self, method, p={}, raise_error=False):
        self.age += 1
        self.lastused = time.time()
        u = list()
        u.append("action=%s" % method)
        if self.session:
            u.append("session=%s" % self.session)
        for k, v in p.items():
            value = v
            if type(v) == int:
                value = "%d" % value
            u.append('%s=%s' % (k, quote_plus(value.encode("utf-8"))))

        url = self.url + '?' + '&'.join(u)
        #cache = ACPClient.CacheWrapper(get_cache('default'))
        cache = None
        h = httplib2.Http(cache, disable_ssl_certificate_validation=True);
        logging.debug(url)
        resp, content = h.request(url, "GET")
        logging.debug(pformat(resp))
        logging.debug(pformat(content))
        if resp.status != 200:
            raise ACPException, resp.reason

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

        return r

    def redirect_to(self, url):
        if self.session:
            return HttpResponseRedirect("%s?session=%s" % (url, self.session))
        else:
            return HttpResponseRedirect(url)

    def login(self, username, password):
        result = self.request('login', {'login': username, 'password': password})
        if result.is_error():
            raise result.exception()
        return result

    def find_or_create_principal(self, key, value, t, d):
        if not self._cache.has_key(t):
            self._cache[t] = {}
        cache = self._cache[t]

        # lxml etree Elements are not picklable
        p = None
        if not cache.has_key(key):
            p = self._find_or_create_principal(key, value, t, d)
            cache[key] = etree.tostring(p)
        else:
            p = etree.parse(StringIO(cache[key])).getroot()
        return p

    def find_principal(self, key, value, t):
        return self.find_or_create_principal(key, value, t, None)

    def _find_or_create_principal(self, key, value, t, d):
        result = self.request('principal-list', {'filter-%s' % key: value, 'filter-type': t}, True)
        principal = result.get_principal()
        if result.is_error():
            if result.status_code() != 'no_data':
                result.exception()
        elif principal and d:
            d['principal-id'] = principal.get('principal-id')

        rp = principal
        if d:
            update_result = self.request('principal-update', d)
            rp = update_result.get_principal()
            if not rp:
                rp = principal
        return rp

    def find_builtin(self, t):
        result = self.request('principal-list', {'filter-type': t}, True)
        return result.get_principal()

    def find_group(self, name):
        result = self.request('principal-list', {'filter-name': name, 'filter-type': 'group'}, True)
        return result.get_principal()

    def find_user(self, login):
        return self.find_principal("login", login, "user")

    def add_remove_member(self, principal_id, group_id, is_member):
        m = "0"
        if is_member:
            m = "1"
        self.request('group-membership-update', {'group-id': group_id, 'principal-id': principal_id, 'is-member': m},
                     True)

    def add_member(self, principal_id, group_id):
        return self.add_remove_member(principal_id, group_id, True)

    def remove_member(self, principal_id, group_id):
        return self.add_remove_member(principal_id, group_id, False)

    def user_counts(self, sco_id):
        user_count = None
        host_count = None
        userlist = self.request('meeting-usermanager-user-list', {'sco-id': sco_id}, False)
        if userlist.status_code() == 'ok':
            user_count = int(userlist.et.xpath("count(.//userdetails)"))
            host_count = int(userlist.et.xpath("count(.//userdetails/role[text() = 'host'])"))
        elif userlist.status_code() == 'no-access' and userlist.subcode() == 'not-available':  #no active session
            user_count = 0
            host_count = 0

        return (user_count, host_count)

    def poll_user_counts(self, room):
        (room.user_count, room.host_count) = self.user_counts(room.sco_id)
        room.save()
        return (room.user_count, room.host_count)