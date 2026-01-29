from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db.models import Q, QuerySet
from django.conf import settings
from impresso.models import UserSpecialMembershipRequest
from impresso.utils.tasks.email import send_templated_email_with_context
from typing import Optional


class Command(BaseCommand):
    """
    Check pending special membership requests for reviewers.

    The reviewer can be:
    - Directly assigned to a UserSpecialMembershipRequest instance
    - Assigned to a SpecialMembershipDataset instance (linked via subscription)

    Usage with pipenv:
    ENV=dev pipenv run ./manage.py checkpendingrequests
    ENV=dev pipenv run ./manage.py checkpendingrequests <username>
    ENV=dev pipenv run ./manage.py checkpendingrequests <username> --send-email
    ENV=dev pipenv run ./manage.py checkpendingrequests <username> --send-email --dry-run

    Usage with docker:
    docker-compose exec <your image name> python manage.py checkpendingrequests
    docker-compose exec <your image name> python manage.py checkpendingrequests <username>

    Example:
    ENV=dev pipenv run ./manage.py checkpendingrequests
    ENV=dev pipenv run ./manage.py checkpendingrequests john.doe
    ENV=dev pipenv run ./manage.py checkpendingrequests john.doe --send-email
    ENV=dev pipenv run ./manage.py checkpendingrequests john.doe --send-email --dry-run
    
    testing:
    ENV=test pipenv run ./manage.py test impresso.tests.management.test_checkpendingrequests
    """

    help = "Check pending special membership requests for a specific reviewer"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "username",
            nargs="?",
            type=str,
            help="Optional username of specific reviewer to check pending requests for",
        )
        parser.add_argument(
            "--send-email",
            action="store_true",
            help="Send email summary to the reviewer",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without actually sending emails",
        )

    def handle(self, username: Optional[str] = None, *args, **options) -> None:
        send_email: bool = options.get("send_email", False)
        dry_run: bool = options.get("dry_run", False)

        self.stdout.write(f"\n{'='*80}")
        if username:
            self.stdout.write(
                f"Looking up reviewer with username: \033[1m{username}\033[0m\n"
            )
        else:
            self.stdout.write("Checking all reviewers for pending requests\n")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No emails will be sent")
            )
        self.stdout.write(f"{'='*80}\n")

        # Fetch the reviewer user(s)
        if username:
            try:
                reviewers = [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ User with username '{username}' does not exist.\n"
                    )
                )
                return
        else:
            # Get all users who have pending requests
            reviewers = self._get_reviewers_with_pending_requests()

        if not reviewers:
            self.stdout.write(
                self.style.WARNING("No reviewers with pending requests found.\n")
            )
            return

        # Process each reviewer
        for reviewer in reviewers:
            self._process_reviewer(reviewer, send_email, dry_run)

        self.stdout.write(f"{'='*80}\n")

        # Query pending requests where:
        # 1. Reviewer is directly assigned to the request, OR
        # 2. Reviewer is assigned to the subscription's dataset
        pending_requests: QuerySet[UserSpecialMembershipRequest] = (
            UserSpecialMembershipRequest.objects.filter(
                status=UserSpecialMembershipRequest.STATUS_PENDING
            )
            .filter(Q(reviewer=reviewer) | Q(subscription__reviewer=reviewer))
            .select_related("user", "reviewer", "subscription")
            .order_by("-date_created")
        )

        request_count: int = pending_requests.count()

        if request_count == 0:
            self.stdout.write(
                self.style.WARNING(
                    f"No pending requests found for reviewer '{reviewer.username}'.\n"
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Found {request_count} pending request{'s' if request_count != 1 else ''}:\n"
            )
        )
        self.stdout.write("=" * 80 + "\n")

        for idx, request in enumerate(pending_requests, start=1):
            self.stdout.write(f"\n{idx}. Request ID: \033[1m{request.pk}\033[0m")
            self.stdout.write(
                f"\n   User: {request.user.username} ({request.user.get_full_name() or 'No name'})"
            )
            self.stdout.write(f"\n   Email: {request.user.email}")
            self.stdout.write(
                f"\n   Subscription: {request.subscription.title if request.subscription else '[deleted subscription]'}"
            )

            # Determine reviewer assignment type
            if request.reviewer == reviewer:
                self.stdout.write(
                    f"\n   Reviewer assignment: \033[1mDirect\033[0m (assigned to request)"
                )
            elif request.subscription and request.subscription.reviewer == reviewer:
                self.stdout.write(
                    f"\n   Reviewer assignment: \033[1mDataset-level\033[0m (assigned to subscription dataset)"
                )
            else:
                self.stdout.write(f"\n   Reviewer assignment: \033[1mOther\033[0m")

            self.stdout.write(f"\n   Status: {request.status}")
            self.stdout.write(
                f"\n   Created: {request.date_created.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.stdout.write(
                f"\n   Last modified: {request.date_last_modified.strftime('%Y-%m-%d %H:%M:%S')}"
            )

            if request.notes:
                # Truncate notes if too long
                notes_preview: str = (
                    request.notes[:100] + "..."
                    if len(request.notes) > 100
                    else request.notes
                )
                self.stdout.write(f"\n   Notes: {notes_preview}")

            self.stdout.write("\n" + "-" * 80)

        self.stdout.write(
            f"\n\n✓ Total pending requests for '{reviewer.username}': \033[1m{request_count}\033[0m\n"
        )

        # Send email if requested
        if send_email:
            self.stdout.write("\n" + "=" * 80 + "\n")

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"[DRY RUN] Would send email summary to {reviewer.email}\n"
                    )
                )
                return

            self.stdout.write("Sending email summary to reviewer...\n")

            if not reviewer.email:
                self.stdout.write(
                    self.style.ERROR(
                        f"✗ Reviewer '{reviewer.username}' has no email address configured.\n"
                    )
                )
                return

            # Get the 3 most recent requests
            latest_requests = list(pending_requests[:3])

            # Prepare email context
            context = {
                "reviewer": reviewer,
                "latest_requests": latest_requests,
                "total_count": request_count,
                "settings": settings,
            }

            # Send email
            try:
                success = send_templated_email_with_context(
                    template="pending_requests_summary_to_reviewer",
                    subject=f"Impresso: {request_count} Pending Special Membership Request{'s' if request_count != 1 else ''}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[reviewer.email],
                    context=context,
                )

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Email successfully sent to {reviewer.email}\n"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.ERROR(
                            f"✗ Failed to send email to {reviewer.email}\n"
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"✗ Error sending email: {str(e)}\n")
                )

    def _get_reviewers_with_pending_requests(self) -> list[User]:
        """Get all reviewers who have pending requests."""
        # Get distinct reviewers from direct assignments
        direct_reviewers = User.objects.filter(
            review__status=UserSpecialMembershipRequest.STATUS_PENDING,
        ).distinct()

        # Get distinct reviewers from dataset assignments
        dataset_reviewers = User.objects.filter(
            reviewed_datasets__userspecialmembershiprequest__status=UserSpecialMembershipRequest.STATUS_PENDING,
        ).distinct()

        # Combine and return unique reviewers
        reviewer_ids = set(direct_reviewers.values_list("id", flat=True)) | set(
            dataset_reviewers.values_list("id", flat=True)
        )
        return list(User.objects.filter(id__in=reviewer_ids))

    def _process_reviewer(
        self, reviewer: User, send_email: bool = False, dry_run: bool = False
    ) -> None:
        """Process a single reviewer and display their pending requests."""
        self.stdout.write(f"\nReviewer: \033[1m{reviewer.username}\033[0m")

        # Query pending requests for this reviewer
        pending_requests: QuerySet[UserSpecialMembershipRequest] = (
            UserSpecialMembershipRequest.objects.filter(
                status=UserSpecialMembershipRequest.STATUS_PENDING
            )
            .filter(Q(reviewer=reviewer) | Q(subscription__reviewer=reviewer))
            .select_related("user", "reviewer", "subscription")
            .order_by("-date_created")
        )

        request_count: int = pending_requests.count()

        if request_count == 0:
            self.stdout.write("  No pending requests")
            return

        self.stdout.write(f"  Found {request_count} pending request(s)")

        for idx, request in enumerate(pending_requests, start=1):
            self.stdout.write(
                f"    {idx}. {request.user.username} - {request.subscription.title if request.subscription else '[deleted]'}"
            )

        # Send email if requested
        if send_email:
            if not reviewer.email:
                self.stdout.write(
                    self.style.WARNING(f"  ✗ No email address configured")
                )
                return

            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [DRY RUN] Would send email to {reviewer.email}"
                    )
                )
                return

            # Get the 3 most recent requests
            latest_requests = list(pending_requests[:3])

            # Prepare email context
            context = {
                "reviewer": reviewer,
                "latest_requests": latest_requests,
                "total_count": request_count,
                "settings": settings,
            }

            # Send email
            try:
                success = send_templated_email_with_context(
                    template="pending_requests_summary_to_reviewer",
                    subject=f"Impresso: {request_count} Pending Special Membership Request{'s' if request_count != 1 else ''}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[reviewer.email],
                    context=context,
                )

                if success:
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✓ Email sent to {reviewer.email}")
                    )
                else:
                    self.stdout.write(self.style.ERROR(f"  ✗ Failed to send email"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {str(e)}"))
