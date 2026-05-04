import logging
from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import Group, User
from django.core import mail
from django.utils import timezone

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.models.profile import Profile
from impresso.models.userBitmap import UserBitmap
from impresso.tasks.userSpecialMembershipRequest_tasks import (
    after_special_membership_request_created,
    revoke_special_membership_request,
)
from impresso.utils.tasks.userSpecialMembershipRequest import (
    send_email_after_user_special_membership_request_created,
)

logger = logging.getLogger("console")


class TestSendCreatedEmailToUserCCReviewer(TestCase):
    """
    Test that when a special membership request is created, an email is sent to the user
    with the reviewer CC'd (Option 1).

    ENV=test pipenv run ./manage.py test impresso.tests.utils.tasks.test_userSpecialMembershipRequest.TestSendCreatedEmailToUserCCReviewer
    """

    def setUp(self):
        self.reviewer = User.objects.create_user(
            username="reviewer",
            first_name="John",
            last_name="Reviewer",
            email="reviewer@example.com",
            password="testpass123",
        )
        self.user = User.objects.create_user(
            username="requester",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="testpass123",
        )

        self.student_group = Group.objects.create(
            name=settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL
        )
        # add user to Student plan group to test plan label in email context
        self.user.groups.add(self.student_group)
        self.profile = Profile.objects.create(user=self.user, uid="local-test-alice")
        self.profile.affiliation = "University of Testing"
        self.profile.save()

        self.dataset = SpecialMembershipDataset.objects.create(
            title="Test Dataset",
            reviewer=self.reviewer,
            metadata={
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
            },
        )
        mail.outbox = []

    def test_created_sends_email_to_user_and_reviewer(self):
        """When request is created, only ONE email should be sent to the user, reviewer in CC."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
            notes="Please review my request.",
        )
        # Set pk and dates manually to avoid triggering signals
        instance.pk = 1
        instance.date_created = instance.date_last_modified = timezone.now()

        send_email_after_user_special_membership_request_created(
            instance=instance,
            logger=logger,
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "ONLY ONE email should be sent, to the user with the reviewer in CC.",
        )
        email = mail.outbox[0]
        self.assertEqual(email.to, ["alice@example.com"])
        self.assertIn("reviewer@example.com", email.cc)
        self.assertEqual(
            email.subject,
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_USER_CC_REVIEWER,
        )
        self.assertIn(
            "Dear Alice Smith,",
            email.body,
            "Email body should contain the user's full name.",
        )
        self.assertIn("Pending Review", email.body)
        self.assertIn("Test Dataset", email.body)

    def test_created_based_on_metadata_modality(self):
        """When request is created with modality in metadata, it should override the function argument."""
        dataset_with_metadata = SpecialMembershipDataset.objects.create(
            title="Metadata Modality Dataset",
            reviewer=self.reviewer,
            metadata={
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
            },
        )
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=None,  # Reviewer on request, should fall back to dataset's reviewer
            subscription=dataset_with_metadata,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = timezone.now()

        send_email_after_user_special_membership_request_created(
            instance=instance,
            logger=logger,
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "ONLY ONE email should be sent based on metadata modality, to the user with the reviewer in CC.",
        )
        email = mail.outbox[0]
        self.assertIn(
            self.reviewer.email,
            email.cc,
            "Reviewer should be in CC based on metadata modality.",
        )

    def test_created_with_already_existing_subscriptions(self):
        """When request is created, the email context should include the correct number of existing special memberships."""
        # Create an existing subscription for the user to test the count in email context
        dataset_existing = SpecialMembershipDataset.objects.create(
            title="Existing Dataset",
            reviewer=self.reviewer,
            metadata={
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
            },
        )
        # we need to create here to ensure signals are triggered and the subscription is counted in the email context
        UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.reviewer,
            subscription=dataset_existing,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )

        self.assertEqual(
            self.user.bitmap.subscriptions.count(),
            1,
            "User should have 1 existing special membership subscription as it is already approved.",
        )

        self.assertIn(
            "Membership Option: Existing Dataset",
            mail.outbox[0].body,
            "Email context should include the correct number of existing special memberships.",
        )

        UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        self.assertIn(
            "Membership Option: Test Dataset",
            mail.outbox[1].body,
            "New datasets!",
        )
        self.assertIn(
            "Number of Special Membership Accesses granted",
            mail.outbox[1].body,
            "Email context should include the correct number of existing special memberships.",
        )


class TestSendCreatedEmailToUserAndReviewer(TestCase):
    """
    Test that when a special membership request is created, emails are sent
    to both the user and the reviewer simultaneously.

    ENV=test pipenv run ./manage.py test impresso.tests.utils.tasks.test_userSpecialMembershipRequest.TestSendCreatedEmailToUserAndReviewer
    """

    def setUp(self):
        self.reviewer = User.objects.create_user(
            username="reviewer",
            first_name="John",
            last_name="Reviewer",
            email="reviewer@example.com",
            password="testpass123",
        )

        self.user = User.objects.create_user(
            username="requester",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            password="testpass123",
        )
        self.student_group = Group.objects.create(
            name=settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER
        )
        # add user to Student plan group to test plan label in email context
        self.user.groups.add(self.student_group)
        self.profile = Profile.objects.create(user=self.user, uid="local-test-alice")
        self.profile.affiliation = "University of Testing"
        self.profile.save()
        self.dataset = SpecialMembershipDataset.objects.create(
            title="Test Dataset", reviewer=self.reviewer, metadata={}
        )
        mail.outbox = []

    def test_created_sends_email_to_user_and_reviewer(self):
        """When request is created, two emails should be sent: one to user, one to reviewer."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
            notes="Please review my request.",
        )
        # Set pk and dates manually to avoid triggering signals
        instance.pk = 1
        instance.date_created = instance.date_last_modified = timezone.now()

        send_email_after_user_special_membership_request_created(
            instance=instance,
            logger=logger,
        )
        self.assertEqual(
            len(mail.outbox),
            2,
            "Two emails should be sent: one to user, one to reviewer",
        )

        # First email: to user
        user_email = mail.outbox[0]
        self.assertEqual(user_email.to, ["alice@example.com"])
        self.assertEqual(
            user_email.subject,
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_USER,
        )
        self.assertIn("Dear Alice,", user_email.body)
        self.assertIn("Pending Review", user_email.body)
        self.assertIn("Test Dataset", user_email.body)
        self.assertIn("Please review my request.", user_email.body)

        # Second email: to reviewer
        reviewer_email = mail.outbox[1]
        self.assertEqual(reviewer_email.to, ["reviewer@example.com"])
        self.assertEqual(
            reviewer_email.subject,
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_REVIEWER,
        )
        self.assertIn("Dear John Reviewer,", reviewer_email.body)
        self.assertIn("Alice Smith", reviewer_email.body)
        self.assertIn("alice@example.com", reviewer_email.body)
        self.assertIn("Test Dataset", reviewer_email.body)

    def test_created_reviewer_email_reply_to_is_user(self):
        """The reviewer email should have reply-to set to the requester's email."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = timezone.now()

        send_email_after_user_special_membership_request_created(
            instance=instance,
            logger=logger,
        )
        reviewer_email = mail.outbox[1]
        self.assertEqual(
            reviewer_email.reply_to,
            ["alice@example.com"],
            "Reply-to should be set to the requester's email for confidential exchange",
        )

    def test_created_reviewer_from_dataset_fallback(self):
        """When no reviewer is set on the request, fall back to the dataset's reviewer."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=None,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = timezone.now()

        send_email_after_user_special_membership_request_created(
            instance=instance,
            logger=logger,
        )
        self.assertEqual(
            len(mail.outbox),
            2,
            "Two emails should be sent even when reviewer comes from dataset",
        )
        reviewer_email = mail.outbox[1]
        self.assertEqual(reviewer_email.to, ["reviewer@example.com"])

    def test_created_no_reviewer_sends_only_user_email(self):
        """When no reviewer can be found, only the user email should be sent."""
        dataset_no_reviewer = SpecialMembershipDataset.objects.create(
            title="No Reviewer Dataset",
            reviewer=None,
        )
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=None,
            subscription=dataset_no_reviewer,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        instance.pk = 2
        instance.date_created = instance.date_last_modified = timezone.now()

        send_email_after_user_special_membership_request_created(
            instance=instance,
            logger=logger,
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "Only user email should be sent when no reviewer is available",
        )
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])

    def test_reviewer_email_html_alternative(self):
        """The reviewer email should include an HTML alternative."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = timezone.now()

        send_email_after_user_special_membership_request_created(
            instance=instance,
            logger=logger,
        )
        reviewer_email = mail.outbox[1]
        self.assertTrue(
            hasattr(reviewer_email, "alternatives"),
            "Email should have HTML alternative",
        )
        self.assertGreater(len(reviewer_email.alternatives), 0)


class TestTemporaryAutomaticAcceptance(TestCase):
    def setUp(self):
        self.reviewer = User.objects.create_user(
            username="temp-reviewer",
            email="temp-reviewer@example.com",
            password="testpass123",
        )
        self.user = User.objects.create_user(
            username="temp-user",
            first_name="Temp",
            email="temp-user@example.com",
            password="testpass123",
        )
        self.dataset = SpecialMembershipDataset.objects.create(
            title="Temporary Dataset",
            reviewer=self.reviewer,
            metadata={
                "enableTemporaryAutomaticAcceptance": True,
                "revokeAfterDays": 7,
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER,
            },
        )
        mail.outbox = []

    def test_created_request_is_auto_approved_temporarily(self):
        req = UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )

        mail.outbox = []
        after_special_membership_request_created(None, req.pk)
        req.refresh_from_db()

        self.assertEqual(
            req.status,
            UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
        )
        self.assertIsNotNone(req.temporary_expires_at)
        self.assertEqual(self.user.bitmap.subscriptions.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_ACCEPTED_TEMPORARY_TO_USER,
        )


class TestTemporaryAutomaticRevocation(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="revoked-user",
            first_name="Revoked",
            email="revoked-user@example.com",
            password="testpass123",
        )
        self.dataset = SpecialMembershipDataset.objects.create(
            title="Revoked Dataset",
            metadata={"revokeAfterDays": 1},
        )
        mail.outbox = []

    def test_expired_temporary_request_is_revoked(self):
        req = UserSpecialMembershipRequest.objects.create(
            user=self.user,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            temporary_expires_at=timezone.now() - timedelta(days=1),
        )
        self.user.bitmap.subscriptions.add(self.dataset)
        mail.outbox = []

        revoke_special_membership_request(None, req.pk)
        req.refresh_from_db()

        self.assertEqual(req.status, UserSpecialMembershipRequest.STATUS_REVOKED)
        self.assertEqual(self.user.bitmap.subscriptions.count(), 0)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_REVOKED_TO_USER,
        )

    def test_revoke_expired_temporary_memberships_beat(self):
        from unittest.mock import patch
        from impresso.tasks.userSpecialMembershipRequest_tasks import revoke_expired_temporary_memberships_beat

        req1 = UserSpecialMembershipRequest.objects.create(
            user=self.user,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            temporary_expires_at=timezone.now() - timedelta(days=1),
        )
        
        user2 = User.objects.create_user(username="other-user")
        req2 = UserSpecialMembershipRequest.objects.create(
            user=user2,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
            temporary_expires_at=timezone.now() + timedelta(days=1),
        )

        with patch("impresso.tasks.userSpecialMembershipRequest_tasks.revoke_special_membership_request.delay") as mock_delay:
            revoke_expired_temporary_memberships_beat(None)
            
            mock_delay.assert_called_once_with(instance_id=req1.pk)
