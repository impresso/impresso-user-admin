"""Change user passwords from a strictly validated TSV file."""

import csv
import re
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction


HEADER = ["username", "password"]
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
PasswordChange = tuple[int, str, str]


class Command(BaseCommand):
    """Change existing users' passwords from a two-column TSV file."""

    help = (
        "Change user passwords from a TSV with one username/password header and "
        "email-address usernames."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "tsv_file",
            type=Path,
            help="Path to a UTF-8 TSV file with username and password columns.",
        )

    def _read_password_changes(self, tsv_file: Path) -> list[PasswordChange]:
        """Read and validate each TSV row before any database mutation."""

        try:
            with tsv_file.open("r", encoding="utf-8", newline="") as file:
                rows = csv.reader(file, delimiter="\t")
                try:
                    header = next(rows)
                except StopIteration as error:
                    raise CommandError("TSV file is empty.") from error

                if header != HEADER:
                    raise CommandError(
                        "TSV header must contain exactly: username<TAB>password."
                    )

                changes: list[PasswordChange] = []
                for line_number, row in enumerate(rows, start=2):
                    if len(row) != len(HEADER):
                        raise CommandError(
                            f"Line {line_number} must contain exactly two columns."
                        )
                    if row == HEADER:
                        raise CommandError(
                            f"Line {line_number} repeats the TSV header."
                        )

                    email, password = row
                    if not EMAIL_PATTERN.fullmatch(email):
                        raise CommandError(
                            f"Line {line_number} has an invalid email address: {email!r}."
                        )
                    changes.append((line_number, email, password))
        except OSError as error:
            raise CommandError(f"Could not read TSV file {tsv_file}: {error}") from error
        except csv.Error as error:
            raise CommandError(f"Invalid TSV file {tsv_file}: {error}") from error

        if not changes:
            raise CommandError("TSV file must contain at least one password-change row.")
        return changes

    def _get_users(self, changes: list[PasswordChange]) -> list[tuple[User, str]]:
        """Ensure every email maps to exactly one existing user before prompting."""

        users: list[tuple[User, str]] = []
        seen_emails: set[str] = set()
        for line_number, email, password in changes:
            if email in seen_emails:
                raise CommandError(f"Line {line_number} repeats email address {email!r}.")
            seen_emails.add(email)

            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist as error:
                raise CommandError(
                    f"Line {line_number}: user with email {email!r} does not exist."
                ) from error
            except User.MultipleObjectsReturned as error:
                raise CommandError(
                    f"Line {line_number}: multiple users have email {email!r}."
                ) from error
            users.append((user, password))
        return users

    def handle(self, tsv_file: Path, *args: str, **options: object) -> None:
        changes = self._read_password_changes(tsv_file)
        users = self._get_users(changes)

        self.stdout.write(
            "\n"
            f"{self.style.WARNING('Password change ready')}\n"
            f"  Users: {len(users)}\n"
            "  Password values will not be displayed.\n"
        )
        answer = input(f"Change passwords for {len(users)} users? [y/N]: ")
        if answer.lower() != "y":
            self.stdout.write(self.style.NOTICE("Password changes cancelled."))
            return

        with transaction.atomic():
            for user, password in users:
                user.set_password(password)
                user.save(update_fields=["password"])

        self.stdout.write(
            self.style.SUCCESS(f"Changed passwords for {len(users)} users.")
        )
