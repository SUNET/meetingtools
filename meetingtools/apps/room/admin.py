'''
Created on Jan 31, 2011

@author: leifj
'''

from django.contrib import admin
from meetingtools.apps.room.models import Room


class RoomAdmin(admin.ModelAdmin):
    date_hierarchy = 'timecreated'
    list_display = ('timecreated', 'creator', 'name', 'urlpath', 'sco', 'deleted_sco', 'lastupdated', 'lastvisited')

admin.site.register(Room, RoomAdmin)