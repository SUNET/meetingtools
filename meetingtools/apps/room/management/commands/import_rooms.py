from django.core.management import BaseCommand
from meetingtools.apps.cluster.models import ACCluster
from meetingtools.apps.room.tasks import import_acc

__author__ = 'leifj'

class Command(BaseCommand):

    def handle(self, *args, **options):
        for acc in ACCluster.objects.all():
            import_acc(acc,since=0)