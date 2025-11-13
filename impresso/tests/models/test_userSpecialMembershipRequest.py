from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone

from impresso.models.userSpecialMembershipRequest import UserSpecialMembershipRequest
from ...models import Profile, SpecialMembershipDataset
from impresso.tasks.userSpecialMembershipRequest_tasks import (
    create_special_membership_request,
)


class UserSpecialMembershipRequestTestCase(TestCase):
    """
    This test simulates the full lifecycle of a user's special membership request
    within the Impresso system, which grants access to specific archive datasets.

    The scenario first verifies that a user with an approved request for Domain A
    does not gain access permissions (reflected by their bitmap value) until they
    explicitly accept the terms.

    It then confirms the subscription is activated and
    the user's bitmap is updated, followed by the revocation of access when the
    request is REJECTED. Finally, the test validates a new request for Domain B,
    confirming no access is granted while the request is PENDING, and verifying
    correct subscription activation and bitmap update upon APPROVAL.
    """

    def setUp(self) -> None:
        self.user = User.objects.create_user(username="testuser-sm", password="12345")
        self.profile = Profile.objects.create(user=self.user, uid="local-testuser-sm")

        self.test_subscription_domain_A = SpecialMembershipDataset.objects.create(
            title="Domain of TEST A archives",
        )
        self.test_subscription_domain_B = SpecialMembershipDataset.objects.create(
            title="Domain of TEST B archives",
        )
        self.test_subscription_domain_C = SpecialMembershipDataset.objects.create(
            title="Domain of TEST C archives",
        )
        self.test_subscription_domain_D = SpecialMembershipDataset.objects.create(
            title="Domain of TEST D archives",
        )

    def test_standard_lifecycle(self) -> None:
        special_membership_request = UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.test_subscription_domain_A.reviewer,
            subscription=self.test_subscription_domain_A,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )

        self.assertEqual(
            self.user.bitmap.get_bitmap_as_int(),
            0b1,
            "The user should have no powers before the terms are accepted.",
        )
        self.assertEqual(
            str(special_membership_request),
            f"{self.user.username} Request for {self.test_subscription_domain_A.title}",
            "The string representation of UserSpecialMembershipRequest is not as expected.",
        )

        self.assertEqual(
            special_membership_request.status,
            UserSpecialMembershipRequest.STATUS_APPROVED,
            "The status of the special membership request should be 'approved'.",
        )
        self.assertEqual(
            self.user.bitmap.get_bitmap_as_int(),
            0b1,
            "Even if subscription is there, the user still should have no powers before the terms are accepted.",
        )
        # things gets updated only if the user has accepted the terms
        self.user.bitmap.date_accepted_terms = timezone.now()
        self.user.bitmap.save()
        # refresh user from db
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.bitmap.subscriptions.count(),
            1,
            "The user should have one subscription after approval.",
        )
        self.assertEqual(
            0b100011,
            self.user.bitmap.get_bitmap_as_int(),
            "The user bitmap should reflect the approved special membership subscription.",
        )
        # Now let's reject the request and see if the subscription is removed
        special_membership_request.status = UserSpecialMembershipRequest.STATUS_REJECTED
        special_membership_request.save()
        # refresh user from db
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.bitmap.subscriptions.count(),
            0,
            "The user should have no subscriptions after rejection.",
        )
        self.assertEqual(
            0b11,
            self.user.bitmap.get_bitmap_as_int(),
            "The user bitmap should reflect the removal of the special membership subscription after rejection.",
        )
        # --- Part 2: Pending Request and Subsequent Approval (Domain B) ---
        special_membership_request_for_B = UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.test_subscription_domain_B.reviewer,
            subscription=self.test_subscription_domain_B,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        self.assertEqual(
            self.user.bitmap.subscriptions.count(),
            0,
            "The user should have no subscriptions while the request is pending.",
        )
        self.assertEqual(
            0b11,
            self.user.bitmap.get_bitmap_as_int(),
            "The user bitmap should remain unchanged while the request is pending.",
        )
        # Now approve it
        special_membership_request_for_B.status = (
            UserSpecialMembershipRequest.STATUS_APPROVED
        )
        special_membership_request_for_B.save()
        # refresh user from db
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.bitmap.subscriptions.count(),
            1,
            "The user should have one subscription after approval of the second request.",
        )
        self.assertEqual(
            0b1000011,
            self.user.bitmap.get_bitmap_as_int(),
            "The user bitmap should reflect the approved special membership subscription for B.",
        )
        # check the changelog!
        self.assertEqual(
            len(special_membership_request_for_B.changelog),
            2,
            "The changelog should have two entries (creation and approval).",
        )
        # --- Part 3: Admin assigns many subscriptions at once. No request is created. ---
        self.user.bitmap.subscriptions.add(
            self.test_subscription_domain_C,
            self.test_subscription_domain_D,
        )
        self.user.bitmap.save()
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.bitmap.subscriptions.count(),
            3,
            "The user should have three subscriptions after admin assignment.",
        )
