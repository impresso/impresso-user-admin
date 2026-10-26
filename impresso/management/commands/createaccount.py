#
# Description:
# django comand that create new active users given a list of emails in the database with randomly generated password. No email is sent.
import random
import re
import secrets
import string
from typing import cast

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from impresso.models import Profile, UserBitmap

ALPHABET: str = string.ascii_letters + string.digits + "-!$"


def generate_four_char_alphanumeric() -> str:
    """Generates a random 4-character alphanumeric string."""

    # 1. Define the character pool (62 total characters)
    CHAR_POOL = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    # 2. Use the randomness from a UUID to choose 4 characters
    # (A simple random choice is sufficient for this purpose)
    return "".join(random.choice(CHAR_POOL) for _ in range(4))


def generate_profile_pattern() -> str:
    """Generate a five-color hexadecimal palette for a user profile."""

    return ",".join(f"#{secrets.token_hex(3)}" for _ in range(5))


class Command(BaseCommand):
    """
    Create bulk user account wih randomly generated password. Needs a list of emails. No email is sent.
    Usage with docker:

    docker-compose exec <your image name> python manage.py createaccount email1 email2 email3
    """

    help = "Create bulk user account wih randomly generated password. Needs a list of emails. No email is sent."
    ANSI_RESET = "\033[0m"
    ANSI_BOLD = "\033[1m"
    ANSI_CYAN = "\033[36m"
    ANSI_YELLOW = "\033[33m"
    ANSI_GREEN = "\033[32m"
    ANSI_RED = "\033[31m"

    def add_arguments(self, parser) -> None:
        parser.add_argument("emails", nargs="+", type=str)
        parser.add_argument(
            "--plan",
            type=str,
            default=None,
            help="Optional plan name for the user profile",
        )
        parser.add_argument(
            "--complete",
            action="store_true",
            default=False,
            help=(
                "Set first and last names from the email local part, split on its "
                "first hyphen."
            ),
        )
        parser.add_argument(
            "--affiliation",
            type=str,
            default=None,
            help="Optional affiliation for the user profile.",
        )
        parser.add_argument(
            "--institutional_url",
            type=str,
            default=None,
            help="Optional institutional URL for the user profile.",
        )
        parser.add_argument(
            "--accept-tou",
            action="store_true",
            default=False,
            help="Record acceptance of the terms of use for each created user.",
        )

    def handle(self, emails: list[str], *args: str, **options: object) -> None:
        plan = cast(str | None, options.get("plan"))
        plan = plan or settings.IMPRESSO_GROUP_USER_PLAN_BASIC
        complete = cast(bool, options["complete"])
        affiliation = cast(str | None, options.get("affiliation"))
        institutional_url = cast(str | None, options.get("institutional_url"))
        accept_tou = cast(bool, options["accept_tou"])

        if plan not in settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS:
            self.stderr.write(
                f"{self.ANSI_RED}{self.ANSI_BOLD}Invalid plan:{self.ANSI_RESET} "
                f"{plan}"
            )
            return
        plan_as_group = Group.objects.get(name=plan)

        users = ["email\tpassword"]
        self.stdout.write(
            "\n"
            f"{self.ANSI_CYAN}{self.ANSI_BOLD}Create Accounts{self.ANSI_RESET}\n"
            f"  Plan: {self.ANSI_BOLD}{plan}{self.ANSI_RESET}\n"
            f"  Complete profiles: {self.ANSI_BOLD}{complete}{self.ANSI_RESET}\n"
            f"  Accept terms of use: {self.ANSI_BOLD}{accept_tou}{self.ANSI_RESET}\n"
        )
        for email in emails:

            pwd = "".join(secrets.choice(ALPHABET) for i in range(16))
            # check if the email is a valid email just with a basic regex
            if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
                self.stdout.write(
                    f"{self.ANSI_RED}{self.ANSI_BOLD}Invalid email:{self.ANSI_RESET} "
                    f"{email}"
                )
                continue
            self.stdout.write(
                f"{self.ANSI_GREEN}{self.ANSI_BOLD}Creating user:{self.ANSI_RESET} "
                f"{self.ANSI_BOLD}{email}{self.ANSI_RESET}"
            )
            self.stdout.write(
                f"{self.ANSI_YELLOW}{self.ANSI_BOLD}Generated password:{self.ANSI_RESET} "
                f"{self.ANSI_BOLD}{pwd}{self.ANSI_RESET}"
            )
            prompt = f"Create user {email} with password {pwd}? [y/N]: "
            ans = input(prompt)
            if ans.lower() != "y":
                self.stdout.write(
                    f"{self.ANSI_YELLOW}{self.ANSI_BOLD}Skipped user creation."
                    f"{self.ANSI_RESET}"
                )
                continue
            # extract username as the first part of the email
            cleaned_email = email.strip()
            username = cleaned_email.split("@")[0]

            user_fields: dict[str, str] = {}
            if complete:
                first_name, _, last_name = username.partition("-")
                user_fields = {
                    "first_name": first_name,
                    "last_name": last_name,
                }

            try:
                user = User.objects.get(username=username)
                created = False
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=username,
                    email=cleaned_email,
                    password=pwd,
                    **user_fields,
                )
                user.is_active = True
                user.save()
                created = True
            else:
                self.stdout.write(
                    f"{self.ANSI_YELLOW}{self.ANSI_BOLD}Username already exists:"
                    f"{self.ANSI_RESET} {username}"
                )
                continue
            # assign the plan to the user
            user.groups.add(plan_as_group)
            if accept_tou:
                UserBitmap.objects.update_or_create(
                    user=user,
                    defaults={"date_accepted_terms": timezone.now()},
                )
            # generate profile uid with prefix "local-" followed by the first two letters of the username and a series of 8 random characters
            profile_uid = f"local-{username[:2]}-{generate_four_char_alphanumeric()}"
            profile_defaults = {
                "uid": profile_uid,
                "pattern": generate_profile_pattern(),
            }
            if affiliation is not None:
                profile_defaults["affiliation"] = affiliation
            if institutional_url is not None:
                profile_defaults["institutional_url"] = institutional_url

            profile, _profile_created = Profile.objects.get_or_create(
                user=user,
                defaults=profile_defaults,
                displayname=f"{first_name} {last_name}" if complete else "Anonymous",
            )
            users.append(f"{email}\t{pwd}")

            # create a profile
            # profile = Profile(user=user)
            # profile.save()
        self.stdout.write()
        self.stdout.write(
            f"{self.ANSI_CYAN}{self.ANSI_BOLD}Account Summary{self.ANSI_RESET}"
        )
        self.stdout.write(f"{self.ANSI_BOLD}{users[0]}{self.ANSI_RESET}")
        self.stdout.write("\n".join(users[1:]))
        self.stdout.write()
