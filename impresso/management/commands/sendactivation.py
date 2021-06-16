from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from impresso.tasks import after_user_activation
from ...utils.tasks.account import send_emails_after_user_activation


class Command(BaseCommand):
    '''
    usage:
    ENV=dev pipenv run ./manage.py sendactivation daniele.guido --immediate
    '''
    help = 'Activate a given User identified by username and send a nice email'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument(
            '--immediate',
            action='store_true',
            help='if true the command does not delay the task with celery',
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
        user.active = True
        if immediate:
            send_emails_after_user_activation(user_id=user.pk)
        else:
            after_user_activation.delay(user_id=user.pk)
        self.stdout.write('---- end ----\n\n')
