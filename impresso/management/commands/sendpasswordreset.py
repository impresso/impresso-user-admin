from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from impresso.tasks import email_password_reset
from ...utils.tasks.account import send_email_password_reset


class Command(BaseCommand):
    """
    usage:
    ENV=dev pipenv run ./manage.py sendpasswordreset daniele.guido token [--immediate] [--callback_url=http://localhost:3000/app/reset-password]
    """

    help = "Send a password reset message to the user identified by username"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str)
        parser.add_argument("token", type=str)
        parser.add_argument(
            "--immediate",
            action="store_true",
            help="if true the command does not delay the task with celery",
        )
        parser.add_argument(
            "--callback_url",
            type=str,
            default="https://impresso-project.ch/app/reset-password",
            help="the base url for the password reset link",
        )

    def handle(
        self, username, token, immediate=False, callback_url="", *args, **options
    ):
        self.stdout.write("\n\n--- start ---")
        user = User.objects.get(username=username)
        self.stdout.write(
            f"user id:{user.pk} uid:{user.profile.uid}"
            f" username:{user.username}"
            f" is_active:{user.is_active}"
            f" token:{token}"
            f" IMMEDIATE:{immediate}"
        )
        self.stdout.write(f"callback_url:{callback_url}")
        if immediate:
            send_email_password_reset(
                user_id=user.pk, token=token, callback_url=callback_url
            )
        else:
            email_password_reset.delay(
                user_id=user.pk, token=token, callback_url=callback_url
            )
        self.stdout.write("---- end ----\n\n")
