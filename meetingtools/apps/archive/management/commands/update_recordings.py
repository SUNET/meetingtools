from django.core.management import BaseCommand
from meetingtools.apps.archive.models import Archive
from meetingtools.apps.cluster.models import ACCluster

__author__ = 'leifj'

class Command(BaseCommand):

    def handle(self, *args, **options):
        for ar in Archive.objects.all():
            info = ar.sco.info()
            if info is None:
                continue
            print info
            if info.has_key('name'):
                ar.name = info['name']
            if info.has_key('description'):
                ar.description = info['description']
            ar.save()
