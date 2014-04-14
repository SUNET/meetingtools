# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from django.db import models, IntegrityError
from django.db.models.fields import CharField, BigIntegerField, IntegerField
from django.db.models.fields.related import ForeignKey
from django.contrib.auth.models import User
from meetingtools.apps.sco.models import ACObject, get_sco
import tagging
from tagging.models import Tag
from django.core.cache import cache


class Content(models.Model):
    creator = ForeignKey(User, editable=False, null=True)
    name = CharField(max_length=128)
    sco = ForeignKey(ACObject, editable=False, null=True, unique=True)
    folder_sco = ForeignKey(ACObject, null=True, related_name="content_folders")
    type = CharField(max_length=128)
    urlpath = CharField(max_length=128)
    bytecount = BigIntegerField()
    created = models.DateTimeField()
    modified = models.DateTimeField()
    views = IntegerField()
    lastviewed = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name_plural = 'Content'

    def __unicode__(self):
        return "%s (sco_id=%s,folder_sco_id=%s,urlpath=%s)" % (self.name, self.sco.sco_id, self.folder_sco.sco_id,
                                                               self.urlpath)

    @staticmethod
    def by_sco(sco):
        return Content.objects.get(sco=sco)

    @staticmethod
    def by_id(acc, sco_id):
        return Content.by_sco(get_sco(acc, sco_id))

    @staticmethod
    def by_name(acc, name):
        return Content.objects.get(sco__acc=acc, name=name)

    def go_url(self):
        return "%s%s" % (self.sco.acc.url, self.urlpath.strip("/"))

    def download_url(self):
        return "%s%s/output/%s.zip?download=zip" % (self.sco.acc.url, self.urlpath.strip("/"), self.urlpath.strip("/"))

    @staticmethod
    def create(acc, api, row):
        sco_id = row.get('sco-id')
        byte_count = api.get_byte_count(sco_id)
        if byte_count or byte_count == 0:
            sco_element = api.get_sco_info(sco_id)
            if sco_element is not None and not sco_element.get('source-sco-id'):  # Object is not a reference
                views = api.get_sco_views(sco_id)
                owner = api.get_owner(sco_element.findtext('url-path'))
                if not owner:
                    owner = get_owner_by_folder(api, acc, sco_element)
                try:
                    domain = owner['login'].split('@')[1]
                    user, created = User.objects.get_or_create(username=owner['login'])
                    if created:
                        user.set_unusable_password()
                except IndexError:
                    user = None
                    domain = None

                datecreated = row.findtext('date-created')
                if not datecreated:
                    datecreated = row.findtext('date-modified')
                try:
                    content, created = Content.objects.get_or_create(
                        sco=get_sco(acc, sco_id),
                        creator=user,
                        name=row.findtext('name'),
                        folder_sco=get_sco(acc, sco_element.get('folder-id')),
                        type=row.get('icon'),
                        urlpath=row.findtext('url'),
                        bytecount=byte_count,
                        created=datecreated,
                        modified=row.findtext('date-modified'),
                        views=views['views'],
                        lastviewed=views['last-viewed-date']
                    )
                except IntegrityError:
                    content = Content.objects.get(sco=get_sco(acc, sco_id))
                    created = False
                if not created:
                    Content.objects.filter(sco=content.sco).update(
                        creator=user,
                        name=row.findtext('name'),
                        folder_sco=get_sco(acc, sco_element.get('folder-id')),
                        type=row.get('icon'),
                        urlpath=row.findtext('url'),
                        bytecount=byte_count,
                        modified=row.findtext('date-modified'),
                        views=views['views'],
                        lastviewed=views['last-viewed-date']
                    )

                if user and domain:
                    tags = []
                    for group in user.groups.all():
                        tags.append("group:%s" % group.name)
                    tags.append("domain:%s" % domain)
                    Tag.objects.update_tags(content, ' '.join(tags))

tagging.register(Content)


def get_owner_by_folder(api, acc, sco):
    default_folders = ['Shared Templates', 'Shared Content', 'User Content', 'Shared Meetings', 'User Meetings',
                       '{tree-type-account-custom}', 'Forced Recordings', 'Chat Transcripts']
    key = 'ac:owner:%s/%s' % (acc, sco.get('sco-id'))
    owner = cache.get(key)
    if owner is None:
        fid = sco.get('folder-id')
        if not fid:
            return None
        folder_id = int(fid)
        r = api.request('sco-info', {'sco-id': folder_id}, False)
        if r.status_code() == 'no-data':
            return None
        parent = r.et.xpath("//sco")[0]
        if parent is not None:
            if parent.findtext('name') in default_folders:
                owner = {
                    'login': sco.findtext('name'),  # To match api.get_owner
                    'sco_id': sco.get('sco-id'),
                }
            else:
                owner = get_owner_by_folder(api, acc, parent)

            if owner is not None:
                cache.set(key, owner, 30)
    return owner