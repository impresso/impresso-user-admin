from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from ...utils.tasks.account import send_emails_after_user_registration


class Command(BaseCommand):
    '''
    usage:
    ENV=dev pipenv run ./manage.py sendconfirmation daniele.guido --immediate
    '''
    help = 'Send activation link to a given User identified by username'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument(
            '--immediate',
            action='store_true',
            help='avoid delay tasks using celery (not use in production)',
        )

    def handle(self, username, immediate=False, *args, **options):
        self.stdout.write('\n\n--- start ---')
        user = User.objects.get(username=username)
        self.stdout.write(
            f'user id:{user.pk} uid:{user.profile.uid}'
            f' username:{user.username}'
            f' is_active:{user.is_active}'
            f' IMMEDIATE:{immediate}'
        )

        if immediate:
            send_emails_after_user_registration(user_id=user.pk)
        self.stdout.write('---- end ----\n\n')
