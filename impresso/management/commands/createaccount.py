#
# Description:
# django comand that create new active users given a list of emails in the database with randomly generated password. No email is sent.
import re
from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand
from impresso.models import Profile
from django.conf import settings
import string
import secrets
import random


ALPHABET: str = string.ascii_letters + string.digits + "-!$"


def generate_four_char_alphanumeric():
    """Generates a random 4-character alphanumeric string."""

    # 1. Define the character pool (62 total characters)
    CHAR_POOL = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    # 2. Use the randomness from a UUID to choose 4 characters
    # (A simple random choice is sufficient for this purpose)
    return "".join(random.choice(CHAR_POOL) for _ in range(4))


class Command(BaseCommand):
    """
    Create bulk user account wih randomly generated password. Needs a list of emails. No email is sent.
    Usage with docker:

    docker-compose exec <your image name> python manage.py createaccount email1 email2 email3
    """

    help = "Create bulk user account wih randomly generated password. Needs a list of emails. No email is sent."

    def add_arguments(self, parser):
        parser.add_argument("emails", nargs="+", type=str)
        parser.add_argument(
            "--plan",
            type=str,
            default=None,
            help="Optional plan name for the user profile",
        )

    def handle(self, emails, *args, **options):
        plan = options.get("plan", settings.IMPRESSO_GROUP_USER_PLAN_BASIC)

        if plan not in settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS:
            self.stderr.write(f"Invalid plan: {plan}")
            return
        plan_as_group = Group.objects.get(name=plan)

        users = ["username\temail\tpassword\tprofile_uid\tstatus"]
        for email in emails:

            pwd = "".join(secrets.choice(ALPHABET) for i in range(16))
            # check if the email is a valid email just with a basic regex
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                self.stdout.write(f"Invalid email: {email}")
                continue
            self.stdout.write(f"Creating user for email: {email}")
            self.stdout.write(f"Generated password: {pwd}")
            prompt = f"Create user {email} with password {pwd}? [y/N]: "
            ans = input(prompt)
            if ans.lower() != "y":
                self.stdout.write("Skipping user creation.")
                continue
            # extract username as the first part of the email
            cleaned_email = email.strip()
            username = cleaned_email.split("@")[0]

            try:
                user = User.objects.get(username=username)
                created = False
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=username,
                    email=cleaned_email,
                    password=pwd,
                )
                user.is_active = True
                user.save()
                created = True
            else:
                self.stdout.write(f"username already exists: {username}")
                continue
            # assign the plan to the user
            user.groups.add(plan_as_group)
            # generate profile uid with prefix "local-" followed by the first two letters of the username and a series of 8 random characters
            profile_uid = f"local-{username[:2]}-{generate_four_char_alphanumeric()}"

            profile, _profile_created = Profile.objects.get_or_create(
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
