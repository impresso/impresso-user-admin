import logging
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User
from impresso.utils.tasks.account import send_email_password_reset
from impresso.utils.tasks.account import send_email_plan_change
from django.core import mail

logger = logging.getLogger("console")


class TestAccound(TestCase):
    """
    Test the task helper for update_user_bitmap_task
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            first_name="Jane",
            last_name="Doe",
            password="12345",
            email="test@test.com",
        )
        # create default groups
        from impresso.signals import create_default_groups

        create_default_groups(sender="impresso")

    def test_send_email_password_reset(self):
        send_email_password_reset(self.user.id, token="test", logger=logger)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Reset password for impresso")
        # clean outbox
        mail.outbox = []

    def test_send_plan_change_exceptions(self):
        with self.assertRaises(ValueError, msg="this plan does not exist"):
            send_email_plan_change(
                user_id=self.user.id,
                plan="not_existing_plan",
                logger=logger,
            )
        with self.assertRaises(User.DoesNotExist, msg="this user does not exist"):
            send_email_plan_change(
                user_id=200000,
                plan="not_existing_plan",
                logger=logger,
            )

    def test_send_email_plan_change(self):
        send_email_plan_change(
            user_id=self.user.id,
            plan=settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL,
            logger=logger,
        )
        self.assertEqual(len(mail.outbox), 2)
        # first email contains this subject
        self.assertEqual(mail.outbox[0].subject, "Change plan for Impresso")
        # first line of the email is: Dear Jane,
        self.assertTrue("Dear Jane," in mail.outbox[0].body)
        # check user is in the right group
        # reload user groups
        self.user.refresh_from_db()
        # get the groups
        self.assertTrue(
            self.user.groups.filter(
                name=settings.IMPRESSO_GROUP_USER_PLAN_REQUEST_EDUCATIONAL
            ),
            "right after the request, user should be associated with the REQUEST for educational group",
        )
        # as the user already requested, successive, probably erroneous requests should not change anything
        send_email_plan_change(
            user_id=self.user.id,
            plan=settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL,
            logger=logger,
        )
        # reload user groups
        self.user.refresh_from_db()
        # get the groups
        self.assertEqual(
            settings.IMPRESSO_GROUP_USER_PLAN_REQUEST_EDUCATIONAL,
            ",".join(self.user.groups.all().values_list("name", flat=True)),
            "Now our user is ONLY ssociated with the REQUEST for educational group",
        )

        # clean outbox
        mail.outbox = []
        send_email_plan_change(
            user_id=self.user.id,
            plan=settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER,
            logger=logger,
        )
        self.assertEqual(len(mail.outbox), 2)
        # first email contains this subject
        self.assertEqual(mail.outbox[0].subject, "Change plan for Impresso")
