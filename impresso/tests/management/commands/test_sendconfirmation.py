from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from impresso.models import Profile


class TestSendConfirmationCommand(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        Profile.objects.create(user=self.user, uid="test-user")

    @patch(
        "impresso.management.commands.sendconfirmation.send_emails_after_user_registration"
    )
    def test_sends_confirmation_with_token_and_callback_url(
        self, mock_send_emails
    ) -> None:
        output = StringIO()
        token = "backend-token"
        callback_url = "https://example.com/confirm-email"

        call_command(
            "sendconfirmation",
            self.user.username,
            token,
            "--callback_url",
            callback_url,
            "--immediate",
            stdout=output,
        )

        mock_send_emails.assert_called_once_with(
            user_id=self.user.pk,
            token=token,
            callback_url=callback_url,
        )
        self.assertIn("---- end ----", output.getvalue())
