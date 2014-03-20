"""
Created on Jan 31, 2011

@author: leifj
"""

from django.contrib import admin
from meetingtools.apps.stats.models import UserMeetingTransaction


class UserMeetingTransactionAdmin(admin.ModelAdmin):
    date_hierarchy = 'date_created'
    list_display = ('date_created', 'date_closed', 'user', 'txid', 'sco')

admin.site.register(UserMeetingTransaction, UserMeetingTransactionAdmin)