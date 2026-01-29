import logging
from io import StringIO
from django.core.management import call_command
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail
from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.signals import create_default_groups


logger = logging.getLogger("console")


class TestCheckPendingRequestsCommand(TestCase):
    """
    Test the checkpendingrequests management command.

    Usage:
    ENV=dev pipenv run ./manage.py test impresso.tests.management.test_checkpendingrequests
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

        # Create another reviewer
        self.other_reviewer = User.objects.create_user(
            username="other_reviewer",
            first_name="Jane",
            last_name="OtherReviewer",
            email="other@example.com",
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

        self.user3 = User.objects.create_user(
            username="user3",
            first_name="Charlie",
            last_name="Brown",
            email="charlie@example.com",
            password="testpass123",
        )

        self.user4 = User.objects.create_user(
            username="user4",
            first_name="Diana",
            last_name="Prince",
            email="diana@example.com",
            password="testpass123",
        )

        # Create special membership datasets
        self.dataset1 = SpecialMembershipDataset.objects.create(
            title="Dataset Alpha",
            reviewer=self.reviewer,
        )

        self.dataset2 = SpecialMembershipDataset.objects.create(
            title="Dataset Beta",
            reviewer=self.other_reviewer,
        )

    def test_command_with_no_pending_requests(self):
        """Test command shows no pending requests when none exist."""
        out = StringIO()
        call_command("checkpendingrequests", "reviewer_user", stdout=out)
        output = out.getvalue()
        self.assertIn("No pending requests", output)

    def test_command_with_optional_username(self):
        """Test command without username shows all reviewers with pending requests."""
        # Create pending request for first reviewer
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        # Create pending request for second reviewer
        UserSpecialMembershipRequest.objects.create(
            user=self.user2,
            reviewer=self.other_reviewer,
            subscription=self.dataset2,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        out = StringIO()
        mail.outbox = []
        call_command("checkpendingrequests", stdout=out)
        output = out.getvalue()

        # Should show both reviewers
        self.assertIn("reviewer_user", output)
        self.assertIn("other_reviewer", output)
        self.assertIn("Found 1 pending request", output)

    def test_command_excludes_non_pending_requests(self):
        """Test that command only shows pending requests, excluding approved/rejected."""
        # Create pending request
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        # Create approved request (should be excluded)
        UserSpecialMembershipRequest.objects.create(
            user=self.user2,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )

        # Create rejected request (should be excluded)
        UserSpecialMembershipRequest.objects.create(
            user=self.user3,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_REJECTED,
        )

        out = StringIO()
        mail.outbox = []
        call_command("checkpendingrequests", "reviewer_user", stdout=out)
        output = out.getvalue()
        self.assertIn("Found 1 pending request", output)
        self.assertIn("Alice Smith", output)
        self.assertNotIn("Bob Jones", output)
        self.assertNotIn("Charlie Brown", output)

    def test_command_send_email_with_multiple_requests(self):
        """Test email sending with multiple pending requests."""
        # Create 4 pending requests
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        UserSpecialMembershipRequest.objects.create(
            user=self.user2,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        UserSpecialMembershipRequest.objects.create(
            user=self.user3,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        UserSpecialMembershipRequest.objects.create(
            user=self.user4,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        mail.outbox = []
        out = StringIO()

        call_command("checkpendingrequests", "reviewer_user", stdout=out)
        output = out.getvalue()

        # Check email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        # Check subject shows total count
        self.assertIn("4 Pending Special Membership Requests", email.subject)

        # Check email shows total count
        self.assertIn("4 pending special membership requests", email.body)

        # Check email shows only top 3 most recent
        self.assertIn("Diana Prince", email.body)
        self.assertIn("Charlie Brown", email.body)
        self.assertIn("Bob Jones", email.body)

        # Check indication of more requests
        self.assertIn("1 more request", email.body)

        # Check HTML email version
        self.assertTrue(hasattr(email, "alternatives"))
        self.assertGreater(len(email.alternatives), 0)

    def test_command_send_email_dry_run(self):
        """Test email sending in dry-run mode does not send emails."""
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            reviewer=self.reviewer,
            subscription=self.dataset1,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        mail.outbox = []
        out = StringIO()
        call_command(
            "checkpendingrequests",
            "reviewer_user",
            "--dry-run",
            stdout=out,
        )
        output = out.getvalue()
        # Check dry run message
        self.assertIn("[DRY RUN] Would send email to", output)
        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)
