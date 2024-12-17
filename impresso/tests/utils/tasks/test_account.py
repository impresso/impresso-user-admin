import logging
from django.conf import settings
from django.test import TestCase
from django.contrib.auth.models import User
from impresso.utils.tasks.account import send_email_password_reset
from django.core import mail

logger = logging.getLogger("console")


class TestAccound(TestCase):
    """
    Test the task helper for update_user_bitmap_task
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", password="12345", email="test@test.com"
        )

    def test_send_email_password_reset(self):
        send_email_password_reset(self.user.id, token="test", logger=logger)
        self.assertEqual(len(mail.outbox), 1)
