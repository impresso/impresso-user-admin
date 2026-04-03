from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.signals import create_default_groups


class TestSendReviewReminderCommand(TestCase):
    """Test the unified sendreviewreminder management command."""

    def setUp(self) -> None:
        create_default_groups(sender="impresso")
        mail.outbox = []

        self.reviewer = User.objects.create_user(
            username="reviewer_user",
            first_name="John",
            last_name="Reviewer",
            email="reviewer@example.com",
            password="testpass123",
        )

        self.user1 = User.objects.create_user(
            username="user1",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="testpass123",
        )

        self.user2 = User.objects.create_user(
            username="user2",
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            password="testpass123",
        )

        self.dataset = SpecialMembershipDataset.objects.create(
            title="Dataset Alpha",
            reviewer=self.reviewer,
        )

    def test_summary_mode_sends_email(self) -> None:
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        mail.outbox = []
        out = StringIO()
        call_command("sendreviewreminder", "summary", "reviewer_user", stdout=out)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Pending Special Membership Request", mail.outbox[0].subject)

    def test_gentle_reminder_mode_applies_days_filter(self) -> None:
        old_request = UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        recent_request = UserSpecialMembershipRequest.objects.create(
            user=self.user2,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        old_date = timezone.now() - timedelta(days=15)
        UserSpecialMembershipRequest.objects.filter(pk=old_request.pk).update(
            date_last_modified=old_date
        )
        UserSpecialMembershipRequest.objects.filter(pk=recent_request.pk).update(
            date_last_modified=timezone.now() - timedelta(days=2)
        )
        mail.outbox = []
        call_command(
            "sendreviewreminder",
            "gentle-reminder",
            "reviewer_user",
            "--days",
            "7",
            stdout=StringIO(),
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(
            "Reminder - 1 Pending Request Needs Review", mail.outbox[0].subject
        )

    def test_preview_mode_does_not_send_email(self) -> None:
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        mail.outbox = []
        out = StringIO()
        call_command(
            "sendreviewreminder",
            "summary",
            "reviewer_user",
            "--preview",
            stdout=out,
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("Email content (text)", out.getvalue())

    def test_preview_mode_html_does_not_send_email(self) -> None:
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        mail.outbox = []
        out = StringIO()
        call_command(
            "sendreviewreminder",
            "summary",
            "reviewer_user",
            "--preview",
            "--preview-mode",
            "html",
            stdout=out,
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("Email content (html)", out.getvalue())

    def test_dry_run_does_not_send_email(self) -> None:
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        mail.outbox = []
        out = StringIO()
        call_command(
            "sendreviewreminder",
            "summary",
            "reviewer_user",
            "--dry-run",
            stdout=out,
        )

        self.assertEqual(len(mail.outbox), 0)
        self.assertIn("[DRY RUN] Would send email to", out.getvalue())
