import logging
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User
from django.core import mail

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest
from impresso.utils.tasks.userSpecialMembershipRequest import (
    send_email_after_user_special_membership_request_updated,
)

logger = logging.getLogger("console")


class TestSendPendingEmailToUserAndReviewer(TestCase):
    """
    Test that when a special membership request is pending, emails are sent
    to both the user and the reviewer simultaneously.

    ENV=test pipenv run ./manage.py test impresso.tests.utils.tasks.test_userSpecialMembershipRequest.TestSendPendingEmailToUserAndReviewer
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
        self.dataset = SpecialMembershipDataset.objects.create(
            title="Test Dataset",
            reviewer=self.reviewer,
        )
        mail.outbox = []

    def test_pending_sends_email_to_user_and_reviewer(self):
        """When status is pending, two emails should be sent: one to user, one to reviewer."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        # Set pk and dates manually to avoid triggering signals
        instance.pk = 1
        instance.date_created = instance.date_last_modified = __import__(
            "django.utils.timezone", fromlist=["now"]
        ).now()

        send_email_after_user_special_membership_request_updated(
            instance=instance, logger=logger
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
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_PENDING_TO_USER,
        )
        self.assertIn("Dear Alice,", user_email.body)
        self.assertIn("Under Review", user_email.body)
        self.assertIn("Test Dataset", user_email.body)

        # Second email: to reviewer
        reviewer_email = mail.outbox[1]
        self.assertEqual(reviewer_email.to, ["reviewer@example.com"])
        self.assertEqual(
            reviewer_email.subject,
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_PENDING_TO_REVIEWER,
        )
        self.assertIn("Dear John,", reviewer_email.body)
        self.assertIn("Alice Smith", reviewer_email.body)
        self.assertIn("alice@example.com", reviewer_email.body)
        self.assertIn("Test Dataset", reviewer_email.body)

    def test_pending_reviewer_email_reply_to_is_user(self):
        """The reviewer email should have reply-to set to the requester's email."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = __import__(
            "django.utils.timezone", fromlist=["now"]
        ).now()

        send_email_after_user_special_membership_request_updated(
            instance=instance, logger=logger
        )
        reviewer_email = mail.outbox[1]
        self.assertEqual(
            reviewer_email.reply_to,
            ["alice@example.com"],
            "Reply-to should be set to the requester's email for confidential exchange",
        )

    def test_pending_reviewer_from_dataset_fallback(self):
        """When no reviewer is set on the request, fall back to the dataset's reviewer."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=None,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_PENDING,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = __import__(
            "django.utils.timezone", fromlist=["now"]
        ).now()

        send_email_after_user_special_membership_request_updated(
            instance=instance, logger=logger
        )
        self.assertEqual(
            len(mail.outbox),
            2,
            "Two emails should be sent even when reviewer comes from dataset",
        )
        reviewer_email = mail.outbox[1]
        self.assertEqual(reviewer_email.to, ["reviewer@example.com"])

    def test_pending_no_reviewer_sends_only_user_email(self):
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
        instance.date_created = instance.date_last_modified = __import__(
            "django.utils.timezone", fromlist=["now"]
        ).now()

        send_email_after_user_special_membership_request_updated(
            instance=instance, logger=logger
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "Only user email should be sent when no reviewer is available",
        )
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])

    def test_approved_sends_only_user_email(self):
        """When status is approved, only the user should get an email."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_APPROVED,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = __import__(
            "django.utils.timezone", fromlist=["now"]
        ).now()

        send_email_after_user_special_membership_request_updated(
            instance=instance, logger=logger
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "Only user email should be sent on approval",
        )
        self.assertEqual(mail.outbox[0].to, ["alice@example.com"])

    def test_rejected_sends_only_user_email(self):
        """When status is rejected, only the user should get an email."""
        instance = UserSpecialMembershipRequest(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.dataset,
            status=UserSpecialMembershipRequest.STATUS_REJECTED,
        )
        instance.pk = 1
        instance.date_created = instance.date_last_modified = __import__(
            "django.utils.timezone", fromlist=["now"]
        ).now()

        send_email_after_user_special_membership_request_updated(
            instance=instance, logger=logger
        )
        self.assertEqual(
            len(mail.outbox),
            1,
            "Only user email should be sent on rejection",
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
        instance.date_created = instance.date_last_modified = __import__(
            "django.utils.timezone", fromlist=["now"]
        ).now()

        send_email_after_user_special_membership_request_updated(
            instance=instance, logger=logger
        )
        reviewer_email = mail.outbox[1]
        self.assertTrue(
            hasattr(reviewer_email, "alternatives"),
            "Email should have HTML alternative",
        )
        self.assertGreater(len(reviewer_email.alternatives), 0)
