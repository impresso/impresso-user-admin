from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from impresso.tasks import test


class Command(BaseCommand):
    help = 'Create a test job with fake progress for a given user'

    def add_arguments(self, parser):
        parser.add_argument('user_id', type=str)

    def handle(self, user_id, *args, **options):
        user = User.objects.get(pk=user_id)

        self.stdout.write('\n\n--- start ---')
        self.stdout.write('user id: "%s"' % user.pk)
        self.stdout.write('user uid: "%s"' % user.profile.uid)

        test.delay(user_id=user.pk)

        self.stdout.write('"test" task launched, check celery.')
        self.stdout.write('---- end ----\n\n')
