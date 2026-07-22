from django.core.management.base import BaseCommand
from impresso.models.userBitmap import UserBitmap
from impresso.tests.utils.tasks.email import User
from impresso.models import SpecialMembershipDataset
from impresso.utils.bitmask import BitMask64


class Command(BaseCommand):
    """
    Subscribe given user by email to special memberships access.

    Usage with pipenv:
    ENV=test pipenv run ./manage.py addspecialmembership email1 email2 email3 --sm 1 2 3

    Usage with docker:
    docker-compose exec <your image name> python manage.py addspecialmembership email1 email2 email3 --sm 1 2 3
    """

    help = "Add special memberships to existing users"

    def add_arguments(self, parser):
        parser.add_argument("emails", nargs="+", type=str)
        parser.add_argument(
            "--sm",
            nargs="*",
            type=int,
            default=None,
            help="Special membership access ids to assign to the users",
        )
        parser.add_argument(
            "--all-sm",
            action="store_true",
            help="Use all special membership access ids.",
        )
        parser.add_argument(
            "--noprompt",
            action="store_true",
            help="Automatic yes to prompts; run non-interactively.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Replace existing special memberships instead of adding.",
        )

    def handle(self, emails, *args, **options):
        raw_special_membership_access_ids = options.get("sm")
        special_membership_access_ids = raw_special_membership_access_ids or []
        sm_provided = raw_special_membership_access_ids is not None
        all_sm = options.get("all_sm", False)
        noprompt = options.get("noprompt", False)
        replace = options.get("replace", False)

        if all_sm:
            if sm_provided:
                self.stdout.write(
                    self.style.WARNING(
                        " Both --all-sm and --sm were provided. Ignoring --sm and using all special memberships."
                    )
                )
            special_membership_access_ids = list(
                SpecialMembershipDataset.objects.values_list("id", flat=True)
            )

        self.stdout.write(
            "\n Starting special membership update process with following args:\n\n"
        )
        self.stdout.write(f"  - Emails:\t\033[1m{emails}\033[0m\n")
        self.stdout.write(
            f"  - access IDs:\t\033[1m{special_membership_access_ids}\033[0m\n"
        )
        self.stdout.write(f"  - All access IDs:\t\033[1m{all_sm}\033[0m\n")
        self.stdout.write(f"  - No Prompt:\t\033[1m{noprompt}\033[0m\n")
        self.stdout.write(f"  - Replace:\t\033[1m{replace}\033[0m\n")

        if not special_membership_access_ids and not replace:
            self.stderr.write(
                " No special memberships provided. Use --sm to specify them. If replace is intended, use --replace flag.\n"
            )
        subscriptions = []
        action = (
            "remove"
            if not special_membership_access_ids and replace
            else "replace" if replace else "remove"
        )
        if not special_membership_access_ids and replace:
            self.stdout.write(
                f"\n No special memberships provided, proceeding to \033[1m{action.upper()}\033[0m all special memberships from the users.\n"
            )
        else:
            self.stdout.write(
                f"\n Preparing to \033[1m{action.upper()}\033[0m following special memberships to users:\n\n"
            )
        for special_membership_access_id in special_membership_access_ids:
            special_membership_access = SpecialMembershipDataset.objects.get(
                id=special_membership_access_id
            )
            self.stdout.write(
                f"  - id: {special_membership_access_id}\t"
                + self.style.SUCCESS(str(special_membership_access))
            )
            subscriptions.append(special_membership_access)
        self.stdout.write("\n")

        if not noprompt:
            confirm_all = input(
                f" Proceed to \033[1m{action}\033[0m the above special memberships to the users? (y/n): "
            )
            if confirm_all.lower() != "y":
                self.stdout.write(
                    self.style.NOTICE("Operation cancelled by user.\n") + "Bye!\n\n"
                )
                return

        for email in emails:
            self.stdout.write("\n--------------------------------------------------\n")
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(
                    f"\n User with email \033[1m{email}\033[0m does not exist. Skipping."
                )
                continue
            if not noprompt:
                confirm = input(
                    f"\n Update special memberships for \033[1m{email}\033[0m? (y/n): "
                )
                if confirm.lower() != "y":
                    continue

            userBitmap, created = UserBitmap.objects.get_or_create(
                user=user,
            )
            user_bitmask = BitMask64(
                userBitmap.get_up_to_date_bitmap(ignore_accepted_terms=True)
            )

            self.stdout.write(
                f"\n user bitmap if terms of use are accepted : \n \033[1m{str(user_bitmask)}\033[0m ({'created' if created else 'existing'})\n"
                f"\n user terms accepted date : \n \033[1m{str(userBitmap.date_accepted_terms)}\033[0m\n\n"
            )
            if replace:
                userBitmap.subscriptions.clear()
                self.stdout.write(
                    f" Cleared existing special memberships for user \033[1m{email}\033[0m."
                )
            for special_membership_access in subscriptions:
                userBitmap.subscriptions.add(special_membership_access)
                self.stdout.write(
                    f" - added special membership \033[1m{str(special_membership_access)}\033[0m to user \033[1m{email}\033[0m."
                )

            userBitmap.save()
            userBitmap.refresh_from_db()
            user_bitmask = BitMask64(
                userBitmap.get_up_to_date_bitmap(ignore_accepted_terms=True)
            )
            self.stdout.write(
                f"\n Updated user bitmap if terms of use are accepted : \n \033[1m{str(user_bitmask)}\033[0m\n"
            )
        self.stdout.write("\n--------------------------------------------------\n")
        self.stdout.write(
            self.style.SUCCESS("\n Special membership update process completed.\n")
        )
