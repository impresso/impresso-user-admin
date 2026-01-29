import logging
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from django.utils import timezone
from datetime import timedelta
from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.signals import create_default_groups


logger = logging.getLogger("console")


class TestRemindPendingRequestsCommand(TestCase):
    """
    Test the remindpendingrequests management command.

    Usage:
    ENV=dev pipenv run ./manage.py test impresso.tests.management.test_remindpendingrequests
    """

    def setUp(self):
        """Set up test fixtures."""
        # Create default groups
        create_default_groups(sender="impresso")

        # Clear mail outbox
        mail.outbox = []

        # Create reviewer user
        self.reviewer = User.objects.create_user(
            username="reviewer_user",
            first_name="John",
            last_name="Reviewer",
            email="reviewer@example.com",
            password="testpass123",
        )

        # Create test users requesting membership
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

        # Create special membership dataset
        self.dataset1 = SpecialMembershipDataset.objects.create(
            title="Dataset Alpha",
            reviewer=self.reviewer,
        )

    def test_command_with_no_old_pending_requests(self):
        """Test that no email is sent when there are no old pending requests."""
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        out = StringIO()
        mail.outbox = []
        call_command("remindpendingrequests", stdout=out)
        output = out.getvalue()
        self.assertIn("No reviewers with old pending requests found", output)
        self.assertEqual(len(mail.outbox), 0)

    def test_command_excludes_non_pending_requests(self):
        """Test that command only considers pending requests."""

        # Create old approved request (should be ignored)
        request1 = UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )
        old_date = timezone.now() - timedelta(days=10)
        UserSpecialMembershipRequest.objects.filter(pk=request1.pk).update(
            date_last_modified=old_date
        )

        # Create old rejected request (should be ignored)
        request2 = UserSpecialMembershipRequest.objects.create(
            user=self.user2,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_REJECTED,
        )
        UserSpecialMembershipRequest.objects.filter(pk=request2.pk).update(
            date_last_modified=old_date
        )
        mail.outbox = []
        out = StringIO()
        call_command("remindpendingrequests", stdout=out)
        output = out.getvalue()

        self.assertIn("No reviewers with old pending requests found", output)
        self.assertEqual(len(mail.outbox), 0)

    def test_command_calculates_days_waiting_correctly(self):
        """Test that days_waiting is calculated correctly in email."""
        # Create request 15 days old
        request = UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        old_date = timezone.now() - timedelta(days=15)
        UserSpecialMembershipRequest.objects.filter(pk=request.pk).update(
            date_last_modified=old_date
        )
        mail.outbox = []
        call_command("remindpendingrequests", stdout=StringIO())

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Check email recipient
        self.assertEqual(email.to, ["reviewer@example.com"])

        # Check that 15 days is mentioned in the email
        self.assertIn("15 days ago", email.body)
