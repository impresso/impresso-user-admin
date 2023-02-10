#
# Description:
# django comand that create new active users given a list of emails in the database with randomly generated password. No email is sent.
import re
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from impresso.models import Profile


class Command(BaseCommand):
    """
    Create bulk user account wih randomly generated password. Needs a list of emails. No email is sent.
    Usage with docker:

    docker-compose exec <your image name> python manage.py createaccount email1 email2 email3
    """

    help = "Create bulk user account wih randomly generated password. Needs a list of emails. No email is sent."

    def add_arguments(self, parser):
        parser.add_argument("emails", nargs="+", type=str)

    def handle(self, emails, *args, **options):
        users = ["username\temail\tpassword\tprofile_uid\tstatus"]
        for email in emails:
            pwd = User.objects.make_random_password()
            # check if the email is a valid email just with a basic regex
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                self.stdout.write(f"Invalid email: {email}")
                continue
            # extract username as the first part of the email
            cleaned_email = email.strip()
            username = cleaned_email.split("@")[0]

            try:
                user = User.objects.get(username=username)
                created = False
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=username, email=cleaned_email, password=pwd
                )
                user.is_active = True
                user.save()
                created = True
            else:
                self.stdout.write(f"username already exists: {username}")
                continue

            # generate profile uid with prefix "local-" followed by the first two letters of the username and a series of 8 random characters
            profile_uid = (
                f"local-{username[:2]}-{User.objects.make_random_password(length=8)}"
            )

            profile, profile_created = Profile.objects.get_or_create(
                user=user, defaults={"uid": profile_uid}
            )
            users.append(
                f'{username}\t{email}\t{pwd}\t{profile.uid}\t{"new" if created else ""}'
            )

            # create a profile
            # profile = Profile(user=user)
            # profile.save()
        self.stdout.write()
        self.stdout.write("\n".join(users))
        self.stdout.write()
