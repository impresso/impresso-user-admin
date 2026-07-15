from typing import Any
from django.core.management.base import BaseCommand
from django.utils import timezone
from impresso.models import UserSpecialMembershipRequest
from impresso.tasks.userSpecialMembershipRequest_tasks import (
    revoke_expired_temporary_memberships,
)

class Command(BaseCommand):
    help = (
        "Check temporary special memberships and enqueue asynchronous revocation for "
        "expired ones."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without making any actual changes to the database.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write(self.style.NOTICE("Running in DRY RUN mode."))

        requests = UserSpecialMembershipRequest.objects.filter(
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY
        )

        count = requests.count()
        self.stdout.write(self.style.SUCCESS(f"Found {count} special memberships with temporary approval."))

        for req in requests:
            expires_at = req.temporary_expires_at
            expired_str = ""
            if expires_at and expires_at < timezone.now():
                expired_str = " (EXPIRED)"
            elif expires_at:
                expired_str = f" (Expires: {expires_at.strftime('%Y-%m-%d %H:%M:%S %Z')})"
                
            dataset_title = req.subscription.title if req.subscription else "None"
            self.stdout.write(
                f"- Request ID: {req.pk}, User: {req.user.username}, "
                f"Dataset: {dataset_title}{expired_str}"
            )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    "Dry run completed: task dispatch skipped."
                )
            )
            return

        async_result = revoke_expired_temporary_memberships.delay()
        self.stdout.write(
            self.style.SUCCESS(
                f"Enqueued revoke_expired_temporary_memberships task (id={async_result.id})."
            )
        )
