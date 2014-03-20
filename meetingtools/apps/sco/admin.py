'''
Created on Jan 31, 2011

@author: leifj
'''

from django.contrib import admin
from meetingtools.apps.sco.models import ACObject


class ACObjectAdmin(admin.ModelAdmin):
    date_hierarchy = 'timecreated'
    list_display = ('timecreated', 'acc', 'sco_id', 'lastupdated', 'is_deleted')


admin.site.register(ACObject, ACObjectAdmin)