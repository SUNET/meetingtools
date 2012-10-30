from optparse import make_option
from django.core.management import BaseCommand
from meetingtools.apps.stats.tasks import import_acc_sessions
from meetingtools.apps.cluster.models import ACCluster

__author__ = 'leifj'

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option('--since',
            type='int',
            dest='since',
            default=0,
            help='Import all sessions <since> seconds ago'),
        )

    def handle(self, *args, **options):
        for acc in ACCluster.objects.all():
            import_acc_sessions(acc,since=options['since'])