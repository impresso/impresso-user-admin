from django.contrib.auth.models import User
from django.test import TestCase
from django.core import mail
from django.conf import settings
from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.models.userBitmap import UserBitmap

from django.utils import timezone


class TestAfterSpecialMembershipRequestCreatedTask(TestCase):
    """
    Test cases for the after_special_membership_request_created task.

    ENV=test pipenv run ./manage.py test impresso.tests.tasks.test_userSpecialMembershipRequest_tasks.TestAfterSpecialMembershipRequestCreatedTask
    """

    def setUp(self) -> None:

        self.johndoe_user = User.objects.create_user(
            username="John Doe",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            password="testpass123",
        )
        self.johndoe_userBitmap = UserBitmap.objects.create(user=self.johndoe_user)
        self.johndoe_userBitmap.date_accepted_terms = timezone.now().replace(
            microsecond=0
        )
        self.johndoe_userBitmap.save()
        self.reviewer_user = User.objects.create_user(
            username="The Reviewer",
            email="alice.reviewer@example.com",
            password="testpass123",
        )
        self.expired_user = User.objects.create_user(
            username="user-with-expired-subscription",
            email="expired@example.com",
            password="testpass123",
        )
        self.active_user = User.objects.create_user(
            username="user-with-active-subscription",
            email="active@example.com",
            password="testpass123",
        )

        self.revokable_not_auto_approval_dataset = SpecialMembershipDataset.objects.create(
            bitmap_position=1,
            title="Revocation Dataset",
            metadata={
                "enableTemporaryAutomaticApproval": False,
                "revokeAfterDays": 1,
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER,
            },
            reviewer=self.reviewer_user,
        )
        self.auto_accept_dataset = SpecialMembershipDataset.objects.create(
            bitmap_position=2,
            title="Auto-Accept Dataset",
            metadata={
                "enableTemporaryAutomaticApproval": True,
                "revokeTemporaryAutomaticApprovalAfterDays": 1,
            },
            reviewer=self.reviewer_user,
        )
        self.revokable_not_auto_approval_cc_reviewer_dataset = SpecialMembershipDataset.objects.create(
            bitmap_position=3,
            title="Revocation Dataset",
            metadata={
                "enableTemporaryAutomaticApproval": False,
                "revokeAfterDays": 1,
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER,
            },
            reviewer=self.reviewer_user,
        )
        # clean outbox
        mail.outbox = []

    def test_create_temporary_request(
        self,
    ) -> None:
        # check user bitmap
        self.assertEqual(
            self.johndoe_userBitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_AUTH_USER,
            f"User must be auth user, got {self.johndoe_userBitmap.get_bitmap_as_int()}",
        )

        # this will trigger post_save_user_special_membership_request signal which will call after_special_membership_request_created task
        UserSpecialMembershipRequest.objects.create(
            user=self.johndoe_user,
            reviewer=self.reviewer_user,
            subscription=self.auto_accept_dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING_TEMPORARY,
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "auto accept dataset should only send the receipt to the user",
        )  # no email should be sent for auto-accepted temporary requests
        self.assertEqual(
            mail.outbox[0].to,
            [self.johndoe_user.email],
            "Email should be sent to the user only",
        )
        self.assertIn(
            "Access will be automatically revoked after 1 day from now",
            mail.outbox[0].body,
        )
        self.johndoe_userBitmap.refresh_from_db()
        self.assertEqual(
            self.johndoe_userBitmap.get_bitmap_as_key_str(),
            "10000011",
            "Auto approbval: User should have temporary special membership bit set",
        )

    def test_create_revokable_not_auto_approval_dataset_request(self) -> None:
        UserSpecialMembershipRequest.objects.create(
            user=self.johndoe_user,
            reviewer=self.reviewer_user,
            subscription=self.revokable_not_auto_approval_dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING_TEMPORARY,
        )
        self.johndoe_userBitmap.refresh_from_db()
        self.assertEqual(
            self.johndoe_userBitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_AUTH_USER,
            "Non-auto-approval: User should NOT have special membership bit set",
        )
        # automatically changed to PENDING by the task, so we check for that
        self.assertEqual(
            UserSpecialMembershipRequest.objects.last().status,
            UserSpecialMembershipRequest.STATUS_PENDING,
            "Non-auto-approval: Request status should be changed to PENDING",
        )
        self.assertEqual(
            self.revokable_not_auto_approval_dataset.metadata.get("modality"),
            settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER,
        )

        self.assertEqual(
            len(mail.outbox),
            2,
            "Non-auto-approval dataset should send the receipt to the user",
        )
        self.assertEqual(
            mail.outbox[1].to,
            [self.reviewer_user.email],
        )

    def test_create_revokable_not_auto_approval_cc_reviewer_dataset(self) -> None:
        UserSpecialMembershipRequest.objects.create(
            user=self.johndoe_user,
            reviewer=self.reviewer_user,
            subscription=self.revokable_not_auto_approval_cc_reviewer_dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        self.johndoe_userBitmap.refresh_from_db()
        self.assertEqual(
            self.johndoe_userBitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_AUTH_USER,
            "Non-auto-approval: User should NOT have special membership bit set",
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "Non-auto-approval dataset should send the receipt to the user",
        )
