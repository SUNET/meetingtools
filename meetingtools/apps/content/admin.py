# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from datetime import date
from django.contrib import admin
from meetingtools.apps.content.models import Content


class YearLastViewedFilter(admin.SimpleListFilter):
    title = 'year last viewed'
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
            return queryset.filter(lastviewed=None)
        try:
            year = int(self.value())
            return queryset.filter(lastviewed__gte=date(year, 1, 1), lastviewed__lte=date(year, 12, 31))
        except TypeError:
            return None


class ContentAdmin(admin.ModelAdmin):
    date_hierarchy = 'created'
    search_fields = ['creator__username', 'name', 'sco__sco_id']
    list_display = ('created', 'creator', 'name', 'type', 'urlpath', 'sco', 'bytecount', 'modified', 'views',
                    'lastviewed')
    list_filter = (YearLastViewedFilter, 'sco__acc',)

admin.site.register(Content, ContentAdmin)