'''
Created on Feb 9, 2011

@author: leifj
'''

from django import template
from meetingtools.settings import PREFIX_URL
register = template.Library()

@register.simple_tag
def prefix():
    return PREFIX_URL