from datetime import timedelta
from io import StringIO
from django.core import mail
from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.signals import create_default_groups


class TestCreateSpecialMembershipRequestCommand(TestCase):
    """Test the createspecialmembershiprequest management command.
    ENV=test pipenv run python manage.py test impresso.tests.management.commands.test_createspecialmembershiprequest.TestCreateSpecialMembershipRequestCommand
    """

    def setUp(self) -> None:
        create_default_groups(sender="impresso")

        self.reviewer = User.objects.create_user(
            username="reviewer",
            first_name="John",
            last_name="Reviewer",
            email="reviewer@example.com",
            password="testpass123",
        )
        self.user = User.objects.create_user(
            username="request-user",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="testpass123",
        )
        self.dataset = SpecialMembershipDataset.objects.create(
            title="Dataset Alpha",
            reviewer=self.reviewer,
        )

    def test_creates_request_with_1_day_revokeable_period(self) -> None:
        out = StringIO()
        dataset_with_revokeable_period = SpecialMembershipDataset.objects.create(
            title="Dataset with Revokeable Period",
            reviewer=self.reviewer,
            metadata={
                "revokeAfterDays": 1,
                "enableTemporaryAutomaticApproval": True,
            },
        )
        mail.outbox = []
        call_command(
            "createspecialmembershiprequest",
            self.user.email,
            str(dataset_with_revokeable_period.pk),
            "--status",
            UserSpecialMembershipRequest.STATUS_PENDING_TEMPORARY,
            stdout=out,
        )
        request = UserSpecialMembershipRequest.objects.get(
            user=self.user,
            subscription=dataset_with_revokeable_period,
        )
        # date dataset_with_revokeable_period should sset and be more or less 24 h from now
        self.assertIsNotNone(request.temporary_expires_at)
        now = request.date_created
        expires_at = request.temporary_expires_at

        self.assertIn(
            "Created special membership request",
            out.getvalue(),
        )

    def test_creates_pending_request_for_user_and_dataset(self) -> None:
        out = StringIO()

        call_command(
            "createspecialmembershiprequest",
            self.user.email,
            str(self.dataset.pk),
            stdout=out,
        )

        request = UserSpecialMembershipRequest.objects.get(
            user=self.user,
            subscription=self.dataset,
        )
        self.assertEqual(request.status, UserSpecialMembershipRequest.STATUS_PENDING)
        self.assertEqual(request.reviewer, self.reviewer)
        self.assertIn(
            "Created special membership request",
            out.getvalue(),
        )

    def test_fails_when_user_does_not_exist(self) -> None:
        with self.assertRaisesMessage(
            CommandError,
            "User with email 'missing@example.com' does not exist.",
        ):
            call_command(
                "createspecialmembershiprequest",
                "missing@example.com",
                str(self.dataset.pk),
            )

    def test_fails_when_dataset_does_not_exist(self) -> None:
        with self.assertRaisesMessage(
            CommandError,
            "SpecialMembershipDataset with id=99999 does not exist.",
        ):
            call_command(
                "createspecialmembershiprequest",
                self.user.email,
                "99999",
            )

    def test_fails_when_request_already_exists(self) -> None:
        UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        with self.assertRaisesMessage(
            CommandError,
            "A request for this user and dataset already exists or could not be created.",
        ):
            call_command(
                "createspecialmembershiprequest",
                self.user.email,
                str(self.dataset.pk),
            )


class TestCreateSpecialMembershipRequestCommandWithOptions(TestCase):
    """Test the createspecialmembershiprequest management command with different options.
    ENV=test pipenv run python manage.py test impresso.tests.management.commands.test_createspecialmembershiprequest.TestCreateSpecialMembershipRequestCommandWithOptions
    """

    def setUp(self) -> None:
        create_default_groups(sender="impresso")

        self.reviewer = User.objects.create_user(
            username="reviewer",
            first_name="John",
            last_name="Reviewer",
            email="reviewer@example.com",
            password="testpass123",
        )
        self.user = User.objects.create_user(
            username="request-user",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="testpass123",
        )
        self.dataset = SpecialMembershipDataset.objects.create(
            title="Dataset Alpha",
            reviewer=self.reviewer,
        )

    def test_add_notes_and_approved_status(self) -> None:
        out = StringIO()
        mail.outbox = []
        call_command(
            "createspecialmembershiprequest",
            self.user.email,
            str(self.dataset.pk),
            "--status",
            UserSpecialMembershipRequest.STATUS_APPROVED,
            "--notes",
            "This is an approved request with notes.",
            stdout=out,
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "Expected only one email to be sent when creating an APPROVED request",
        )
        self.assertEqual(mail.outbox[0].to, [self.user.email])
        self.assertIn("approved", mail.outbox[0].subject.lower())

        request = UserSpecialMembershipRequest.objects.get(
            user=self.user,
            subscription=self.dataset,
        )

        self.assertEqual(request.status, UserSpecialMembershipRequest.STATUS_APPROVED)
        self.assertEqual(request.reviewer, self.reviewer)
        self.assertIn(
            "Created special membership request",
            out.getvalue(),
        )

    def test_add_notes_and_approved_temporary_status(self) -> None:
        out = StringIO()
        mail.outbox = []
        call_command(
            "createspecialmembershiprequest",
            self.user.email,
            str(self.dataset.pk),
            "--status",
            UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            "--notes",
            "This is an approved request with notes.",
            stdout=out,
        )
        # check user_bitmap.subscriptions
        request = UserSpecialMembershipRequest.objects.get(
            user=self.user,
            subscription=self.dataset,
        )
        self.user.refresh_from_db()
        self.assertEqual(
            request.status, UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY
        )
        self.assertEqual(request.reviewer, self.reviewer)
        self.assertEqual(request.notes, "This is an approved request with notes.")
        self.assertEqual(self.user.bitmap.subscriptions.count(), 1)

    def test_create_pending_when_temporary_automatic_acceptance_is_enabled(
        self,
    ) -> None:
        revokable_dataset = SpecialMembershipDataset.objects.create(
            title="Revokable Dataset",
            reviewer=self.reviewer,
            metadata={
                "revokeAfterDays": 5,
                "enableTemporaryAutomaticApproval": True,
            },
        )
        out = StringIO()
        mail.outbox = []
        call_command(
            "createspecialmembershiprequest",
            self.user.email,
            "--status",
            UserSpecialMembershipRequest.STATUS_PENDING_TEMPORARY,
            str(revokable_dataset.pk),
            stdout=out,
        )
        request = UserSpecialMembershipRequest.objects.get(
            user=self.user,
            subscription=revokable_dataset,
        )
        self.assertEqual(
            request.status, UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY
        )
        self.assertTrue(
            request.temporary_expires_at is not None,
            "temporary_expires_at should be set for temporary approved requests",
        )
        self.assertEqual(
            request.temporary_expires_at.date(),
            (
                timezone.now()
                + timedelta(
                    days=revokable_dataset.resolve_temporary_automatic_approval_after_days(
                        default_days=1
                    )
                )
            ).date(),
            "temporary_expires_at should be approximately now + 5 days",
        )

    def test_revoke_after_half_day_sets_temporary_expires_at(self) -> None:
        """
        --revoke-after 0.5 should set temporary_expires_at to approximately now + 12 hours.
        """
        out = StringIO()
        before = timezone.now()
        call_command(
            "createspecialmembershiprequest",
            self.user.email,
            str(self.dataset.pk),
            "--revoke-after",
            "0.5",
            "--status",
            UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            stdout=out,
        )
        after = timezone.now()

        request = UserSpecialMembershipRequest.objects.get(
            user=self.user,
            subscription=self.dataset,
        )
        self.assertIsNotNone(request.temporary_expires_at)

        expected_lower = before + timedelta(days=0.5)
        expected_upper = after + timedelta(days=0.5)

        self.assertGreaterEqual(
            request.temporary_expires_at,
            expected_lower,
            "temporary_expires_at should be at least now + 0.5 days",
        )
        self.assertLessEqual(
            request.temporary_expires_at,
            expected_upper,
            "temporary_expires_at should be at most now + 0.5 days",
        )
        self.assertIn("Created special membership request", out.getvalue())
        self.assertIn("Access will be automatically revoked after", mail.outbox[0].body)
        # Revocation is asynchronous, so only the temporary-approval email is sent here.
        self.assertEqual(
            len(mail.outbox),
            1,
            "Expected one email to be sent: temporary approval notification",
        )
