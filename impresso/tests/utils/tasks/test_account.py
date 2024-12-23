import logging
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User
from impresso.models import UserChangePlanRequest
from impresso.models import UserBitmap
from impresso.utils.tasks.account import (
    send_email_password_reset,
    send_email_plan_change,
    send_email_plan_change_accepted,
    send_email_plan_change_rejected,
)
from django.utils import timezone
from django.core import mail

logger = logging.getLogger("console")


class TestAccount(TestCase):
    """
    Test the task helper for update_user_bitmap_task
    ENV=dev pipenv run ./manage.py test impresso.tests.utils.tasks.test_account
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

        req = UserChangePlanRequest.objects.get(user=self.user)

        self.assertEqual(req.status, UserChangePlanRequest.STATUS_PENDING)
        self.assertEqual(req.plan.name, settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL)
        # clean outbox
        mail.outbox = []
        # accept the request
        req.status = UserChangePlanRequest.STATUS_APPROVED
        req.save()
        # manually send the email
        send_email_plan_change_accepted(
            user_id=self.user.id, plan=req.plan.name, logger=logger
        )
        self.assertEqual(len(mail.outbox), 1)
        # Check that the body starts with Dear Jane, and contains the settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL
        self.assertTrue("Dear Jane," in mail.outbox[0].body)
        self.assertTrue(
            settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL in mail.outbox[0].body,
            f"should receive corrrect email:f{mail.outbox[0].body}",
        )

        # get user bitmap
        user_bitmap = UserBitmap.objects.get(user=self.user)

        self.assertEqual(
            user_bitmap.get_bitmap_as_int(),
            UserBitmap.USER_PLAN_GUEST,
            "user is Guest auntill they accept the terms",
        )
        # accept the terms
        user_bitmap.date_accepted_terms = timezone.now()
        user_bitmap.save()
        user_bitmap.refresh_from_db()
        self.assertEqual(
            str(user_bitmap),
            f"testuser Bitmap {bin(UserBitmap.USER_PLAN_EDUCATIONAL)}",
            "User plan USER_PLAN_EDUCATIONAL activated!",
        )

        # now we manually reject the request, as approving was an error
        req.status = UserChangePlanRequest.STATUS_REJECTED
        req.notes = "Wrong acceptance!"
        req.save()
        user_bitmap.refresh_from_db()
        self.assertEqual(
            str(user_bitmap),
            f"testuser Bitmap {bin(UserBitmap.USER_PLAN_AUTH_USER)}",
            "User plan back to USER_PLAN_AUTH_USER !",
        )
        mail.outbox = []
        send_email_plan_change_rejected(
            user_id=self.user.id, plan=req.plan.name, logger=logger
        )
        self.assertEqual(len(mail.outbox), 1)

        self.assertTrue("Dear Jane," in mail.outbox[0].body)
        self.assertTrue("rejected" in mail.outbox[0].body)
        self.assertTrue(
            settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL in mail.outbox[0].body,
            f"should receive corrrect email:f{mail.outbox[0].body}",
        )
