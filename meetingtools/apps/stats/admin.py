'''
Created on Jan 31, 2011

@author: leifj
'''

from django.contrib import admin
from meetingtools.apps.stats.models import UserMeetingTransaction

admin.site.register(UserMeetingTransaction)