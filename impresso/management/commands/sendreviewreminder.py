from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Q, QuerySet
from django.utils import timezone

from impresso.models import UserSpecialMembershipRequest
from impresso.utils.tasks.email import (
    get_emails_rendered_contents,
    send_templated_email_with_context,
)


class Command(BaseCommand):
    """
    Send reviewer emails about pending special membership requests.

    Modes:
    - summary: include all pending requests
    - gentle-reminder: include only pending requests older than --days

    Usage:
    ENV=dev pipenv run ./manage.py sendreviewreminder summary
    ENV=dev pipenv run ./manage.py sendreviewreminder gentle-reminder --days 14
    ENV=dev pipenv run ./manage.py sendreviewreminder summary john.doe --dry-run
    """

    MODE_SUMMARY = "summary"
    MODE_GENTLE_REMINDER = "gentle-reminder"

    help = (
        "Send reviewer summary or gentle-reminder emails for pending special "
        "membership requests"
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "mode",
            type=str,
            choices=[self.MODE_SUMMARY, self.MODE_GENTLE_REMINDER],
            help="Email mode: summary or gentle-reminder",
        )
        parser.add_argument(
            "username",
            nargs="?",
            type=str,
            help="Optional username of specific reviewer",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help=(
                "Minimum days a request must be pending for gentle-reminder mode "
                "(default: 7)"
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be sent without actually sending emails",
        )
        parser.add_argument(
            "--preview",
            action="store_true",
            help="Preview email txt content without sending emails",
        )
        parser.add_argument(
            "--preview-mode",
            type=str,
            choices=["txt", "html"],
            default="txt",
            help="Select preview output format when --preview is used (default: txt)",
        )

    def handle(
        self,
        mode: str,
        username: Optional[str] = None,
        *args,
        **options,
    ) -> None:
        days_threshold: int = options.get("days", 7)
        dry_run: bool = options.get("dry_run", False)
        preview: bool = options.get("preview", False)
        preview_mode: str = options.get("preview_mode", "txt")

        cutoff_date = None
        if mode == self.MODE_GENTLE_REMINDER:
            cutoff_date = timezone.now() - timedelta(days=days_threshold)

        self.stdout.write(
            self.style.HTTP_INFO("\nRunning sendreviewreminder command with:\n")
            + self.style.SUCCESS(
                f"mode={mode}, days={days_threshold}, dry_run={dry_run}, "
                f"preview={preview}, preview_mode={preview_mode}, username={username}\n"
            )
        )

        if mode == self.MODE_GENTLE_REMINDER:
            self.stdout.write(f"Targeting requests older than {days_threshold} day(s)")
        else:
            self.stdout.write("Targeting all pending requests")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No emails will be sent")
            )
        if preview:
            self.stdout.write(
                self.style.WARNING(
                    f"PREVIEW MODE - {preview_mode.upper()} email content will be displayed"
                )
            )

        reviewers = self._get_reviewers(username=username, cutoff_date=cutoff_date)

        if not reviewers:
            self.stdout.write(
                self.style.WARNING(
                    "No reviewers with matching pending requests found.\n"
                )
            )
            return

        self.stdout.write(f"\nFound {len(reviewers)} reviewer(s) to process\n")

        total_emails_sent = 0
        for idx, reviewer in enumerate(reviewers, start=1):
            self.stdout.write(
                f"\n{idx} of {len(reviewers)} - Reviewer: <{reviewer.email}> "
                f"(username: {reviewer.username})"
            )
            self.stdout.write(f"\n{'-' * 80}")
            sent = self._process_reviewer(
                reviewer=reviewer,
                mode=mode,
                cutoff_date=cutoff_date,
                dry_run=dry_run,
                preview=preview,
                preview_mode=preview_mode,
            )
            if sent:
                total_emails_sent += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK DRY RUN: Would have sent {total_emails_sent} email(s)\n"
                )
            )
        elif preview:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK PREVIEW: Displayed email content for "
                    f"{total_emails_sent} reviewer(s)\n"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK Successfully sent {total_emails_sent} email(s)\n"
                )
            )

    def _get_reviewers(
        self,
        username: Optional[str],
        cutoff_date,
    ) -> List[User]:
        if username:
            try:
                return [User.objects.get(username=username)]
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"User with username '{username}' does not exist.")
                )
                return []

        direct_query = {
            "review__status": UserSpecialMembershipRequest.STATUS_PENDING,
        }
        dataset_query = {
            "reviewed_datasets__userspecialmembershiprequest__status": UserSpecialMembershipRequest.STATUS_PENDING,
        }

        if cutoff_date is not None:
            direct_query["review__date_last_modified__lt"] = cutoff_date
            dataset_query[
                "reviewed_datasets__userspecialmembershiprequest__date_last_modified__lt"
            ] = cutoff_date

        direct_reviewers = User.objects.filter(**direct_query).distinct()
        dataset_reviewers = User.objects.filter(**dataset_query).distinct()

        reviewer_ids = set(direct_reviewers.values_list("id", flat=True)) | set(
            dataset_reviewers.values_list("id", flat=True)
        )
        return list(User.objects.filter(id__in=reviewer_ids))

    def _process_reviewer(
        self,
        reviewer: User,
        mode: str,
        cutoff_date,
        dry_run: bool,
        preview: bool,
        preview_mode: str,
    ) -> bool:
        if not reviewer.email:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipping: {reviewer.username} has no email address configured"
                )
            )
            return False

        pending_requests: QuerySet[UserSpecialMembershipRequest] = (
            UserSpecialMembershipRequest.objects.filter(
                status=UserSpecialMembershipRequest.STATUS_PENDING,
            )
            .filter(Q(reviewer=reviewer) | Q(subscription__reviewer=reviewer))
            .select_related("user", "reviewer", "subscription")
        )

        if cutoff_date is not None:
            pending_requests = pending_requests.filter(
                date_last_modified__lt=cutoff_date
            )
            pending_requests = pending_requests.order_by("date_last_modified")
            info_label = "old pending"
        else:
            pending_requests = pending_requests.order_by("-date_created")
            info_label = "pending"

        request_count = pending_requests.count()

        if request_count == 0:
            self.stdout.write(f"No {info_label} requests for {reviewer.username}")
            return False

        self.stdout.write(f"Found {request_count} {info_label} request(s)")

        latest_requests = list(pending_requests[:3])

        now = timezone.now()
        for request in latest_requests:
            request.days_waiting = (now - request.date_last_modified).days

        if mode == self.MODE_GENTLE_REMINDER:
            template = "pending_requests_reminder_to_reviewer"
            subject = (
                f"Impresso: Reminder - {request_count} Pending Request"
                f"{'s' if request_count != 1 else ''} Need"
                f"{'s' if request_count == 1 else ''} Review"
            )
        else:
            template = "pending_requests_summary_to_reviewer"
            subject = (
                f"Impresso: {request_count} Pending Special Membership Request"
                f"{'s' if request_count != 1 else ''}"
            )

        context: Dict[str, Any] = {
            "reviewer": reviewer,
            "latest_requests": latest_requests,
            "count_latest_requests": len(latest_requests),
            "total_count": request_count,
            "settings": settings,
        }

        if preview:
            txt_content, html_content = get_emails_rendered_contents(
                prefix=template, context=context
            )
            preview_content = html_content if preview_mode == "html" else txt_content
            content_label = "html" if preview_mode == "html" else "text"
            self.stdout.write(
                f"\nEmail content ({content_label}):\n\n{preview_content}\n"
            )
            return True

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"[DRY RUN] Would send email to {reviewer.email}")
            )
            self.stdout.write(f"Subject: {subject}")
            return True

        try:
            success = send_templated_email_with_context(
                template=template,
                subject=subject,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[reviewer.email],
                context=context,
            )
        except Exception as exc:
            self.stdout.write(
                self.style.ERROR(f"Error sending email to {reviewer.email}: {str(exc)}")
            )
            return False

        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Reminder email sent to {reviewer.email}")
            )
            return True

        self.stdout.write(self.style.ERROR(f"Failed to send email to {reviewer.email}"))
        return False
