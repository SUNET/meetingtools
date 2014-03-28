'''
Created on Jan 31, 2011

@author: leifj
'''

from datetime import date
from django.contrib import admin
from meetingtools.apps.room.models import Room


class YearLastVisitedFilter(admin.SimpleListFilter):
    title = 'year last visited'
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        return (
            ('None', 'None'),
            ('2009', '2009'),
            ('2010', '2010'),
            ('2011', '2011'),
            ('2012', '2012'),
            ('2013', '2013'),
            ('2014', '2014'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'None':
            return queryset.filter(lastvisited=None)
        try:
            year = int(self.value())
            return queryset.filter(lastvisited__gte=date(year, 1, 1), lastvisited__lte=date(year, 12, 31))
        except TypeError:
            return None


class RoomAdmin(admin.ModelAdmin):
    date_hierarchy = 'timecreated'
    search_fields = ['creator__username', 'name', 'sco__sco_id']
    list_display = ('timecreated', 'creator', 'name', 'urlpath', 'sco', 'deleted_sco', 'lastupdated', 'lastvisited')
    list_filter = (YearLastVisitedFilter, 'sco__acc',)

admin.site.register(Room, RoomAdmin)