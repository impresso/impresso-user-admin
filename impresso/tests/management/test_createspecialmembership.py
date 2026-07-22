from io import StringIO

from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.conf import settings

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.signals import create_default_groups


class TestCreateSpecialMembershipCommand(TestCase):
    """Test the createspecialmembership management command.
    ENV=test ./manage.py test impresso.tests.management.test_createspecialmembership
    """

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

        self.user = User.objects.create_user(
            username="testuser",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="testpass123",
        )

        self.dataset = SpecialMembershipDataset.objects.create(
            title="Dataset Alpha",
            reviewer=self.reviewer,
            bitmap_position=9,
            metadata={
                "modality": "cc_reviewer",
                "description": "Test dataset for special membership",
            },
        )

        self.dataset_without_reviewer = SpecialMembershipDataset.objects.create(
            title="Dataset Without Reviewer",
            reviewer=None,
            bitmap_position=10,
        )

    def test_create_special_membership_request_success(self) -> None:
        """Test successful creation of a special membership request."""
        out = StringIO()
        call_command(
            "createspecialmembership",
            str(self.dataset.id),
            "testuser",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("Creating special membership request", output)
        self.assertIn(f"dataset_id={self.dataset.id}", output)
        self.assertIn("username=testuser", output)
        self.assertIn("Created request id=", output)
        self.assertIn("status='pending'", output)
        self.assertIn("Reviewer email: reviewer@example.com", output)
        self.assertIn("cc_reviewer", output)

        request = UserSpecialMembershipRequest.objects.get(
            user=self.user, subscription=self.dataset
        )
        self.assertEqual(request.status, UserSpecialMembershipRequest.STATUS_PENDING)
        self.assertEqual(request.reviewer, self.reviewer)
        self.assertIsNone(request.notes)

    def test_create_with_notes(self) -> None:
        """Test creating a special membership request with notes."""
        out = StringIO()
        notes = "Please expedite this request."
        call_command(
            "createspecialmembership",
            str(self.dataset.id),
            "testuser",
            "--notes",
            notes,
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn(f"Notes: {notes}", output)
        self.assertIn("Created request id=", output)

        request = UserSpecialMembershipRequest.objects.get(
            user=self.user, subscription=self.dataset
        )
        self.assertEqual(request.notes, notes)

    def test_create_existing_request_returns_existing(self) -> None:
        """Test that creating a request for an existing subscription returns the existing record."""
        UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        self.assertIn("Dear Alice Smith", mail.outbox[0].body)
        self.assertIn("Dear John Reviewer,", mail.outbox[0].body)
        self.assertEqual(
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_USER_CC_REVIEWER,
            mail.outbox[0].subject,
        )
        mail.outbox = []

        out = StringIO()
        call_command(
            "createspecialmembership",
            str(self.dataset.id),
            "testuser",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("Request already exists", output)
        self.assertIn("returning existing record", output)

        self.assertEqual(
            UserSpecialMembershipRequest.objects.filter(
                user=self.user, subscription=self.dataset
            ).count(),
            1,
        )

    def test_dataset_metadata_in_output(self) -> None:
        """Test that dataset metadata is displayed in command output."""
        out = StringIO()
        call_command(
            "createspecialmembership",
            str(self.dataset.id),
            "testuser",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("Dataset metadata:", output)
        self.assertIn("cc_reviewer", output)
        self.assertIn("Test dataset for special membership", output)

    def test_dataset_with_no_reviewer(self) -> None:
        """Test creating request for dataset with no reviewer assigned."""
        dataset_no_reviewer = SpecialMembershipDataset.objects.create(
            title="Dataset Without Reviewer",
            reviewer=None,
            bitmap_position=11,
        )

        out = StringIO()
        call_command(
            "createspecialmembership",
            str(dataset_no_reviewer.id),
            "testuser",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("Reviewer email: None", output)
        self.assertIn("Created request id=", output)

        request = UserSpecialMembershipRequest.objects.get(
            user=self.user, subscription=dataset_no_reviewer
        )
        self.assertIsNone(request.reviewer)

    def test_signal_triggers_email_on_creation(self) -> None:
        """Test that creating request triggers post_save signal and sends email."""
        mail.outbox = []
        out = StringIO()
        call_command(
            "createspecialmembership",
            str(self.dataset.id),
            "testuser",
            stdout=out,
        )

        # Verify email was sent due to post_save signal
        self.assertGreater(
            len(mail.outbox),
            0,
            "Post-save signal should trigger email sending task.",
        )

    def test_empty_metadata_displayed(self) -> None:
        """Test creating request for dataset with empty metadata."""
        dataset_empty_metadata = SpecialMembershipDataset.objects.create(
            title="Dataset Empty Metadata",
            reviewer=self.reviewer,
            bitmap_position=12,
            metadata={},
        )

        out = StringIO()
        call_command(
            "createspecialmembership",
            str(dataset_empty_metadata.id),
            "testuser",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("Dataset metadata: {}", output)
