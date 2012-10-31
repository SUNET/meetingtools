from optparse import make_option
from django.core.management import BaseCommand
from meetingtools.apps.cluster.models import ACCluster
from meetingtools.apps.room.tasks import import_acc

__author__ = 'leifj'

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--since',
            type='int',
            dest='since',
            default=0,
            help='Import all rooms modified <since> seconds ago'),
        make_option('--cluster',
            type='int',
            dest='cluster',
            default=0,
            help='Import rooms from cluster <cluster> (id)'),
        )

    def handle(self, *args, **options):
        qs = ACCluster.objects
        if options['cluster'] > 0:
            qs = qs.filter(pk=options['cluster'])
        for acc in qs.all():
            import_acc(acc,since=options['since'])