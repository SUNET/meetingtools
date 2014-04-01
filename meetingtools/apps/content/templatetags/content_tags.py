# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django import template
import math

register = template.Library()


def humanize_bytes(b):
    try:
        size_name = ('B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB')
        i = int(math.floor(math.log(b, 1024)))
        p = math.pow(1024, i)
        s = round(b / p, 2)
        if s > 0:
            return '%s %s' % (s, size_name[i])
    except TypeError:
        return 'TypeError'

register.filter('humanize_bytes', humanize_bytes)