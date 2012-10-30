import logging
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from iso8601 import iso8601
import tagging
from tagging.models import Tag
from meetingtools.apps.sco.models import ACObject, get_sco

__author__ = 'leifj'

from django.db import models
from django.db.models import fields, ForeignKey, DateTimeField, IntegerField
import lxml.etree as etree

class UserMeetingTransaction(models.Model):
    sco = ForeignKey(ACObject)
    user = ForeignKey(User)
    txid = IntegerField()
    date_created = DateTimeField()
    date_closed = DateTimeField()

    def seconds(self):
        delta = self.date_closed - self.date_created
        return delta.total_seconds()

    def __unicode__(self):
        return "(%d) %d seconds in %s" % (self.txid,self.seconds(),self.sco)

    @staticmethod
    def create(acc,row):
        txid = int(row.get('transaction-id'))
        sco_id = int(row.get('sco-id'))

        status = row.findtext("status")
        if not status or status != "completed":
            logging.debug("Ignoring transaction %s" % etree.tostring(row))
            return

        txo = None
        try:
            txo = UserMeetingTransaction.objects.get(sco__acc=acc,txid=txid)
        except MultipleObjectsReturned,ex:
            logging.error(ex)
        except ObjectDoesNotExist:
            login = row.findtext("login")
            if not login:
                raise ValueError("No user for transaction %d" % txid)
            user,created = User.objects.get_or_create(username=login)
            date_created=iso8601.parse_date(row.findtext("date-created"))
            #date_created = date_created.replace(tzinfo=None)
            date_closed=iso8601.parse_date(row.findtext("date-closed"))
            #date_close = date_closed.replace(tzinfo=None)
            txo = UserMeetingTransaction.objects.create(sco=get_sco(acc,sco_id),
                                                        txid=txid,
                                                        user=user,
                                                        date_created=date_created,
                                                        date_closed=date_closed)
        tags = []
        for group in txo.user.groups.all():
            tags.append("group:%s" % group.name)

        (local,domain) = txo.user.username.split("@")
        tags.append("domain:%s" % domain)
        Tag.objects.update_tags(txo, ' '.join(tags))

tagging.register(UserMeetingTransaction)