from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q, QuerySet
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from typing import List, Dict, Any, Optional
from impresso.models import UserSpecialMembershipRequest
from impresso.utils.tasks.email import send_templated_email_with_context


class Command(BaseCommand):
    """
    Send reminder emails to reviewers for pending special membership requests
    that have been waiting for more than 7 days.

    The reviewer can be:
    - Directly assigned to a UserSpecialMembershipRequest instance
    - Assigned to a SpecialMembershipDataset instance (linked via subscription)

    Usage with pipenv:
    ENV=dev pipenv run ./manage.py remindpendingrequests
    ENV=dev pipenv run ./manage.py remindpendingrequests <username>
    ENV=dev pipenv run ./manage.py remindpendingrequests --days 14

    Usage with docker:
    docker-compose exec <your image name> python manage.py remindpendingrequests
    docker-compose exec <your image name> python manage.py remindpendingrequests <username>

    Example:
    ENV=dev pipenv run ./manage.py remindpendingrequests
    ENV=dev pipenv run ./manage.py remindpendingrequests john.doe
    ENV=dev pipenv run ./manage.py remindpendingrequests --days 14 --dry-run

    testing:
    ENV=test pipenv run ./manage.py test impresso.tests.management.test_remindpendingrequests
    """

    help = "Send reminder emails to reviewers for pending requests older than specified days"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "username",
            nargs="?",
            type=str,
            help="Optional username of specific reviewer to remind",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Minimum days a request must be pending to trigger reminder (default: 7)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without actually sending emails",
        )

    def handle(self, username: Optional[str] = None, *args, **options) -> None:
        days_threshold: int = options.get("days", 7)
        dry_run: bool = options.get("dry_run", False)

        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(
            f"Starting reminder process for requests older than \033[1m{days_threshold} days\033[0m"
        )
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No emails will be sent")
            )
        self.stdout.write(f"{'='*80}\n")

        # Calculate cutoff date
        cutoff_date = timezone.now() - timedelta(days=days_threshold)

        # Get reviewers to process
        if username:
            # Process specific reviewer
            try:
                reviewers = [User.objects.get(username=username)]
                self.stdout.write(
                    f"Processing specific reviewer: \033[1m{username}\033[0m\n"
                )
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ User with username '{username}' does not exist.\n"
                    )
                )
                return
        else:
            # Get all reviewers with old pending requests
            reviewers = self._get_reviewers_with_old_pending_requests(cutoff_date)
            self.stdout.write(
                f"Found \033[1m{len(reviewers)}\033[0m reviewer(s) with old pending requests\n"
            )

        if not reviewers:
            self.stdout.write(
                self.style.WARNING("No reviewers with old pending requests found.\n")
            )
            return

        # Process each reviewer
        total_emails_sent = 0
        for reviewer in reviewers:
            result = self._process_reviewer(reviewer, cutoff_date, dry_run)
            if result:
                total_emails_sent += 1

        # Summary
        self.stdout.write(f"\n{'='*80}")
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ DRY RUN: Would have sent {total_emails_sent} reminder email(s)\n"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Successfully sent {total_emails_sent} reminder email(s)\n"
                )
            )
        self.stdout.write(f"{'='*80}\n")

    def _get_reviewers_with_old_pending_requests(self, cutoff_date) -> List[User]:
        """Get all reviewers who have pending requests older than cutoff date."""
        # Get distinct reviewers from direct assignments
        direct_reviewers = User.objects.filter(
            review__status=UserSpecialMembershipRequest.STATUS_PENDING,
            review__date_last_modified__lt=cutoff_date,
        ).distinct()

        # Get distinct reviewers from dataset assignments
        dataset_reviewers = User.objects.filter(
            reviewed_datasets__userspecialmembershiprequest__status=UserSpecialMembershipRequest.STATUS_PENDING,
            reviewed_datasets__userspecialmembershiprequest__date_last_modified__lt=cutoff_date,
        ).distinct()

        # Combine and return unique reviewers
        reviewer_ids = set(direct_reviewers.values_list("id", flat=True)) | set(
            dataset_reviewers.values_list("id", flat=True)
        )
        return list(User.objects.filter(id__in=reviewer_ids))

    def _process_reviewer(
        self, reviewer: User, cutoff_date, dry_run: bool = False
    ) -> bool:
        """Process a single reviewer and send reminder email if needed."""
        self.stdout.write(f"\nProcessing reviewer: \033[1m{reviewer.username}\033[0m")

        # Query pending requests older than cutoff date
        pending_requests: QuerySet[UserSpecialMembershipRequest] = (
            UserSpecialMembershipRequest.objects.filter(
                status=UserSpecialMembershipRequest.STATUS_PENDING,
                date_last_modified__lt=cutoff_date,
            )
            .filter(Q(reviewer=reviewer) | Q(subscription__reviewer=reviewer))
            .select_related("user", "reviewer", "subscription")
            .order_by("date_last_modified")  # Oldest first
        )

        request_count: int = pending_requests.count()

        if request_count == 0:
            self.stdout.write(f"  No old pending requests for {reviewer.username}")
            return False

        self.stdout.write(f"  Found {request_count} old pending request(s)")

        # Check if reviewer has email
        if not reviewer.email:
            self.stdout.write(
                self.style.WARNING(
                    f"  ✗ Skipping: {reviewer.username} has no email address configured"
                )
            )
            return False

        # Get the 3 oldest requests
        latest_requests = list(pending_requests[:3])

        # Calculate days waiting for each request
        now = timezone.now()
        for request in latest_requests:
            days_waiting = (now - request.date_last_modified).days
            request.days_waiting = days_waiting

        # Prepare email context
        context: Dict[str, Any] = {
            "reviewer": reviewer,
            "latest_requests": latest_requests,
            "total_count": request_count,
            "settings": settings,
        }

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"  [DRY RUN] Would send reminder email to {reviewer.email}"
                )
            )
            self.stdout.write(
                f"    Subject: Impresso: Reminder - {request_count} Pending Request(s) Need Review"
            )
            return True

        # Send email
        try:
            success = send_templated_email_with_context(
                template="pending_requests_reminder_to_reviewer",
                subject=f"Impresso: Reminder - {request_count} Pending Request{'s' if request_count != 1 else ''} Need{'s' if request_count == 1 else ''} Review",
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[reviewer.email],
                context=context,
            )

            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Reminder email sent to {reviewer.email}")
                )
                return True
            else:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Failed to send email to {reviewer.email}")
                )
                return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"  ✗ Error sending email to {reviewer.email}: {str(e)}"
                )
            )
            return False
