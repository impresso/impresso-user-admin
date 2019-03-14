import requests, json
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from impresso.models import Job, Attachment

from impresso.tasks import export_query_as_csv
from django.conf import settings


class Command(BaseCommand):
    help = 'Create a test job with fake progress for a given user'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=str)
        parser.add_argument('q', type=str)

    def handle(self, user_id, q, *args, **options):
        user = User.objects.get(pk=user_id)

        self.stdout.write('\n\n--- start ---')
        self.stdout.write('user id: "%s"' % user.pk)
        self.stdout.write('user uid: "%s"' % user.profile.uid)
        self.stdout.write('query: (%s)' % q)

        export_query_as_csv.delay(query=q, user_id=user_id)

        self.stdout.write('"test" task launched, check celery.')
        self.stdout.write('---- end ----\n\n')
