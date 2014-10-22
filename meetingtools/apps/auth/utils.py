"""
Created on Jul 7, 2010

@author: leifj
"""

from uuid import uuid4
from django.conf import settings as django_settings


def nonce():
    return uuid4().hex


def anonid():
    return uuid4().urn


def groups(request):
    groups = []
    if request.user.is_authenticated():
        groups = request.user.groups

    return groups


def report_auth(request):
    auth_data = request.META.get('HTTP_X_REPORT_AUTH', None)
    if auth_data and ':' in auth_data:
        report_users = getattr(django_settings, 'REPORT_USERS')
        requester, key = auth_data.split(':')
        if report_users[requester]['key'] == key:
            return report_users[requester]
    return False