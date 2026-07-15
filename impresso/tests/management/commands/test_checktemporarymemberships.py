from datetime import timedelta
from io import StringIO
from django.core import mail
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.signals import create_default_groups

from unittest.mock import patch


class TestCheckTemporaryMembershipsCommand(TestCase):
    """Test the checktemporarymemberships management command.
    ENV=test pipenv run python manage.py test impresso.tests.management.commands.test_checktemporarymemberships.TestCheckTemporaryMembershipsCommand
    """

    def setUp(self) -> None:
        create_default_groups(sender="impresso")

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
        )

    def test_finds_temporary_memberships(self) -> None:
        # Create one pending, one temporary approved
        # pending request should not be included in the output, only the temporary approved one
        UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "Always expect an email to be sent when creating a request",
        )  # Debug assertion to check mail outbox length
        mail.outbox = []
        # Clear the outbox before creating the temporary approved request

        temp_req = UserSpecialMembershipRequest.objects.create(
            user=self.user2,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            temporary_expires_at=timezone.now() + timedelta(days=7),
        )
        self.assertEqual(len(mail.outbox), 1)

        out = StringIO()
        with patch(
            "impresso.management.commands.checktemporarymemberships.revoke_expired_temporary_memberships.delay"
        ) as mock_delay:
            call_command("checktemporarymemberships", stdout=out)
            mock_delay.assert_called_once_with()

        output = out.getvalue()
        self.assertIn("Found 1 special memberships with temporary approval.", output)
        self.assertIn(f"Request ID: {temp_req.pk}", output)
        self.assertIn("User: user2", output)
        self.assertIn("Dataset: Dataset Alpha", output)
        self.assertIn("(Expires:", output)
        self.assertIn("Enqueued revoke_expired_temporary_memberships task", output)

    def test_shows_expired_memberships(self) -> None:
        # Create a temporary approved request that has already expired

        temp_req = UserSpecialMembershipRequest.objects.create(
            user=self.user1,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            temporary_expires_at=timezone.now() - timedelta(days=1),
        )

        out = StringIO()
        call_command("checktemporarymemberships", stdout=out)

        output = out.getvalue()
        self.assertIn("Found 1 special memberships with temporary approval.", output)
        self.assertIn(f"Request ID: {temp_req.pk}", output)
        self.assertIn("(EXPIRED)", output)

    def test_dry_run_flag(self) -> None:
        out = StringIO()
        call_command("checktemporarymemberships", "--dry-run", stdout=out)

        output = out.getvalue()
        self.assertIn("Running in DRY RUN mode.", output)
        self.assertIn("Found 0 special memberships with temporary approval.", output)
        self.assertIn("Dry run completed: task dispatch skipped.", output)
