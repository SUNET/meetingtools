from django.core.exceptions import ImproperlyConfigured

__author__ = 'leifj'

from django.conf import settings
import logging

def theme(request):

    def _w(x):
        return {'theme': x}

    vhost = request.get_host()
    vhost = vhost.replace(':','_')

    ctx = {'vhost': vhost}
    if hasattr(settings,'THEMES'):
        if settings.THEMES.has_key(vhost):
            ctx.update(settings.THEMES[vhost])
        elif settings.THEMES.has_key('__default__'):
            ctx.update(settings.THEMES['__default__'])

    return _w(ctx)

def misc_urls(request):
    return {'LOGIN_URL': settings.LOGIN_URL}