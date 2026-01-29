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
            "--dry-run",
            action="store_true",
            help="Show what would be sent without actually sending emails",
        )

    def handle(self, username: Optional[str] = None, *args, **options) -> None:
        dry_run: bool = options.get("dry_run", False)

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
            all_pending_requests: QuerySet[UserSpecialMembershipRequest] = (
                UserSpecialMembershipRequest.objects.filter(
                    status=UserSpecialMembershipRequest.STATUS_PENDING
                )
            )
            # get all reviewers or subscription__reviewer
            reviewers_ids = set(
                all_pending_requests.values_list("reviewer_id", flat=True)
            ).union(
                set(
                    all_pending_requests.values_list(
                        "subscription__reviewer_id", flat=True
                    )
                )
            )
            reviewers = User.objects.filter(id__in=reviewers_ids)

        if not reviewers:
            self.stdout.write(
                self.style.WARNING("No reviewers with pending requests found.\n")
            )
            return

        # Process each reviewer
        for reviewer in reviewers:
            self._process_reviewer(reviewer, dry_run)

    def _process_reviewer(self, reviewer: User, dry_run: bool = False) -> None:
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

        self.stdout.write(
            self.style.WARNING(f"Found {request_count} pending request(s)")
        )

        for idx, request in enumerate(pending_requests):
            self.stdout.write(f"\n{idx + 1}. Request ID: \033[1m{request.pk}\033[0m")
            self.stdout.write(
                f"   User: {request.user.username} ({request.user.get_full_name() or 'No name'})"
            )
            self.stdout.write(f"   Email: {request.user.email}")
            self.stdout.write(
                f"   Subscription: {request.subscription.title if request.subscription else '[deleted subscription]'}"
            )
            # Determine reviewer assignment type
            if request.reviewer == reviewer:
                self.stdout.write(
                    f"   Reviewer assignment: \033[1mDirect\033[0m (assigned to request)"
                )
            elif request.subscription and request.subscription.reviewer == reviewer:
                self.stdout.write(
                    f"   Reviewer assignment: \033[1mDataset-level\033[0m (assigned to subscription dataset)"
                )
            else:
                self.stdout.write(f"   Reviewer assignment: \033[1mOther\033[0m")

            self.stdout.write(f"   Status: {request.status}")

        # Send email if requested
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"\n[DRY RUN] Would send email to {reviewer.email}")
            )
            return
        if not reviewer.email:
            self.stdout.write(self.style.WARNING(f"  ✗ No email address configured"))
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
                    self.style.SUCCESS(f"\n✓ Email sent to {reviewer.email}")
                )
            else:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to send email"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Error: {str(e)}"))
