# -*- coding: utf-8 -*-
__author__ = 'lundberg'

from meetingtools.ac import ac_api_client
from django.core.cache import cache
import logging
from datetime import datetime, timedelta


def get_owner(api, acc, sco):
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
                owner = get_owner(api, acc, parent)

            if owner is not None:
                cache.set(key, owner, 30)

    return owner


def import_acc(acc, since=0):
    result = []
    with ac_api_client(acc) as api:
        if since > 0:
            then = datetime.now()-timedelta(seconds=since)
            then = then.replace(microsecond=0)
            r = api.request('report-bulk-objects',
                            {'filter-out-type': 'meeting', 'filter-gt-date-modified': then.isoformat()})
        else:
            r = api.request('report-bulk-objects', {'filter-out-type': 'meeting'})
        if r:
            nr = 0
            for row in r.et.xpath("//row"):
                sco_id = row.get('sco-id')
                byte_count = api.get_byte_count(sco_id)
                if byte_count or byte_count == 0:
                    sco_element = api.get_sco_info(sco_id)
                    if not sco_element.get('source-sco-id'):  # Object is not a reference
                        owner = api.get_owner(sco_element.findtext('url-path'))
                        if not owner:
                            owner = get_owner(api, acc, sco_element)
                        views = api.get_sco_views(sco_id)
                        item = {
                            'sco-id': sco_id,
                            'folder-id': sco_element.get('folder-id'),
                            'type': row.get('icon'),
                            'name': row.findtext('name'),
                            'byte_count': byte_count,
                            'url-path': row.findtext('url'),
                            'created': row.findtext('date-created'),
                            'modified': row.findtext('date-modified'),
                            'owner': owner,
                            'views': views,
                        }
                        result.append(item)
                        nr += 1
            logging.info("%s: Imported %d objects." % (acc, nr))
        return result
