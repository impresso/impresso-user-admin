from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.tasks.userSpecialMembershipRequest_tasks import (
    revoke_expired_temporary_memberships,
)


class TestRevokeExpiredTemporaryMembershipsBeat(TestCase):
    def setUp(self) -> None:
        self.dataset = SpecialMembershipDataset.objects.create(
            bitmap_position=9,
            title="Beat Revocation Dataset",
            metadata={"revokeAfterDays": 1},
        )
        self.expired_user = User.objects.create_user(
            username="expired-user",
            email="expired@example.com",
            password="testpass123",
        )
        self.active_user = User.objects.create_user(
            username="active-user",
            email="active@example.com",
            password="testpass123",
        )

    def test_beat_updates_bitmap_counts_for_expired_requests(self) -> None:
        expired_request = UserSpecialMembershipRequest.objects.create(
            user=self.expired_user,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            temporary_expires_at=timezone.now() - timedelta(days=1),
        )
        active_request = UserSpecialMembershipRequest.objects.create(
            user=self.active_user,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            temporary_expires_at=timezone.now() + timedelta(days=1),
        )

        self.expired_user.refresh_from_db()
        self.active_user.refresh_from_db()

        self.assertEqual(self.expired_user.bitmap.subscriptions.count(), 1)
        self.assertEqual(self.active_user.bitmap.subscriptions.count(), 1)

        revoke_expired_temporary_memberships.delay()

        expired_request.refresh_from_db()
        active_request.refresh_from_db()
        self.expired_user.refresh_from_db()
        self.active_user.refresh_from_db()

        self.assertEqual(
            expired_request.status, UserSpecialMembershipRequest.STATUS_REVOKED
        )
        self.assertEqual(
            active_request.status,
            UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
        )
        self.assertEqual(self.expired_user.bitmap.subscriptions.count(), 0)
        self.assertEqual(self.active_user.bitmap.subscriptions.count(), 1)
