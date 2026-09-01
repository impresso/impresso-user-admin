from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.signals import create_default_groups


@override_settings(IMPRESSO_BASE_URL="https://admin.example.test")
class TestRevokeMembershipAccessCommand(TestCase):
    def setUp(self) -> None:
        create_default_groups(sender="impresso")

        self.user_revokable = User.objects.create_user(
            username="revokable-user",
            email="revokable@example.com",
            password="testpass123",
        )
        self.user_active = User.objects.create_user(
            username="active-user",
            email="active@example.com",
            password="testpass123",
        )
        self.user_non_revokable = User.objects.create_user(
            username="non-revokable-user",
            email="non-revokable@example.com",
            password="testpass123",
        )

        self.dataset_revokable = SpecialMembershipDataset.objects.create(
            bitmap_position=7,
            title="Dataset Revokable",
            metadata={"revokeAfterDays": 3},
        )
        self.dataset_active = SpecialMembershipDataset.objects.create(
            bitmap_position=6,
            title="Dataset Active",
            metadata={"revokeAfterDays": 7},
        )
        self.dataset_missing_metadata = SpecialMembershipDataset.objects.create(
            bitmap_position=5,
            title="Dataset Missing Metadata",
            metadata={},
        )

    def _set_request_created_at(
        self, request: UserSpecialMembershipRequest, created_at
    ) -> None:
        UserSpecialMembershipRequest.objects.filter(pk=request.pk).update(
            date_created=created_at
        )
        request.refresh_from_db()

    def _get_expected_admin_url(self, request_id: int) -> str:
        return "https://admin.example.test" + reverse(
            "admin:impresso_userspecialmembershiprequest_change", args=[request_id]
        )

    def test_dry_run_reports_requests_without_mutation(self) -> None:
        revokable_request = UserSpecialMembershipRequest.objects.create(
            user=self.user_revokable,
            subscription=self.dataset_revokable,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )
        self._set_request_created_at(
            revokable_request, timezone.now() - timedelta(days=10)
        )

        out = StringIO()
        call_command("revokemembershipaccess", "--dry-run", stdout=out)

        revokable_request.refresh_from_db()

        self.assertEqual(
            revokable_request.status, UserSpecialMembershipRequest.STATUS_APPROVED
        )
        output = out.getvalue()
        self.assertIn("Running in DRY RUN mode.", output)
        self.assertIn("Found 1 special memberships with approved status.", output)
        self.assertIn(f"Request ID: {revokable_request.pk}", output)
        self.assertIn(self._get_expected_admin_url(revokable_request.pk), output)
        self.assertIn("Revocation needed", output)
        self.assertIn("Dry run completed: 1 revocations need implementation.", output)

    def test_revokes_expired_approved_request_and_updates_bitmap(self) -> None:
        revokable_request = UserSpecialMembershipRequest.objects.create(
            user=self.user_revokable,
            subscription=self.dataset_revokable,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )
        active_request = UserSpecialMembershipRequest.objects.create(
            user=self.user_active,
            subscription=self.dataset_active,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )
        self._set_request_created_at(
            revokable_request, timezone.now() - timedelta(days=10)
        )
        self._set_request_created_at(active_request, timezone.now() - timedelta(days=1))

        self.user_revokable.refresh_from_db()
        self.user_active.refresh_from_db()
        self.assertEqual(self.user_revokable.bitmap.subscriptions.count(), 1)
        self.assertEqual(self.user_active.bitmap.subscriptions.count(), 1)

        out = StringIO()
        call_command("revokemembershipaccess", stdout=out)

        revokable_request.refresh_from_db()
        active_request.refresh_from_db()
        self.user_revokable.refresh_from_db()
        self.user_active.refresh_from_db()

        self.assertEqual(
            revokable_request.status, UserSpecialMembershipRequest.STATUS_REVOKED
        )
        self.assertEqual(
            active_request.status, UserSpecialMembershipRequest.STATUS_APPROVED
        )
        self.assertEqual(self.user_revokable.bitmap.subscriptions.count(), 0)
        self.assertEqual(self.user_active.bitmap.subscriptions.count(), 1)

        output = out.getvalue()
        self.assertIn("Found 2 special memberships with approved status.", output)
        self.assertIn(f"Request ID: {revokable_request.pk}", output)
        self.assertIn(f"Request ID: {active_request.pk}", output)
        self.assertIn(self._get_expected_admin_url(revokable_request.pk), output)
        self.assertIn(self._get_expected_admin_url(active_request.pk), output)
        self.assertIn("Revocation needed", output)
        self.assertIn("ACTIVE:", output)
        self.assertIn(
            "Revoked 1 approved special memberships that needed revocation.", output
        )

    def test_keeps_recent_approved_request_active(self) -> None:
        active_request = UserSpecialMembershipRequest.objects.create(
            user=self.user_active,
            subscription=self.dataset_active,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )
        self._set_request_created_at(active_request, timezone.now() - timedelta(days=2))

        out = StringIO()
        call_command("revokemembershipaccess", stdout=out)

        active_request.refresh_from_db()

        self.assertEqual(
            active_request.status, UserSpecialMembershipRequest.STATUS_APPROVED
        )
        output = out.getvalue()
        self.assertIn(self._get_expected_admin_url(active_request.pk), output)
        self.assertIn("ACTIVE:", output)
        self.assertIn(
            "Revoked 0 approved special memberships that needed revocation.", output
        )

    def test_reports_non_revokable_requests_with_missing_metadata(self) -> None:
        non_revokable_request = UserSpecialMembershipRequest.objects.create(
            user=self.user_non_revokable,
            subscription=self.dataset_missing_metadata,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )
        self._set_request_created_at(
            non_revokable_request, timezone.now() - timedelta(days=30)
        )

        out = StringIO()
        call_command("revokemembershipaccess", stdout=out)

        non_revokable_request.refresh_from_db()
        self.user_non_revokable.refresh_from_db()

        self.assertEqual(
            non_revokable_request.status, UserSpecialMembershipRequest.STATUS_APPROVED
        )
        self.assertEqual(self.user_non_revokable.bitmap.subscriptions.count(), 1)

        output = out.getvalue()
        self.assertIn(f"Request ID: {non_revokable_request.pk}", output)
        self.assertIn(self._get_expected_admin_url(non_revokable_request.pk), output)
        self.assertIn("NON-REVOKABLE", output)
        self.assertIn(
            "Revoked 0 approved special memberships that needed revocation.", output
        )
