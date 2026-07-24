from urllib.parse import urlparse

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings

from impresso.models import Profile
from impresso.utils.tasks.account import (
    build_email_validation_link,
    send_emails_after_user_registration,
)


class TestEmailValidation(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser-validation",
            first_name="Jane",
            last_name="Doe",
            email="validation@test.com",
        )
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])
        self.profile = Profile.objects.create(
            user=self.user,
            uid="local-testuser-validation",
        )

    def _get_validation_link_from_email(self) -> str:
        mail.outbox = []
        send_emails_after_user_registration(self.user.id)
        validation_link = next(
            (
                line.strip()
                for line in mail.outbox[0].body.splitlines()
                if "/validate-email/?" in line
            ),
            None,
        )
        if validation_link is None:
            self.fail("Expected a validation link in the email")
        return validation_link

    @override_settings(IMPRESSO_BASE_URL="https://example.com")
    def test_build_email_validation_link(self):
        validation_link = build_email_validation_link(self.user)
        parsed = urlparse(validation_link)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "example.com")
        self.assertEqual(parsed.path, "/validate-email/")
        self.assertIn("token=", parsed.query)

    def test_send_emails_after_user_registration_contains_validation_link(self):
        validation_link = self._get_validation_link_from_email()

        self.assertIn("/validate-email/?token=", validation_link)
        self.assertIn(validation_link, mail.outbox[0].alternatives[0][0])

    def test_validate_email_marks_profile_without_activating_user(self):
        validation_link = self._get_validation_link_from_email()
        parsed = urlparse(validation_link)

        response = self.client.get(f"{parsed.path}?{parsed.query}")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Email address verified", response.content.decode())

        self.profile.refresh_from_db()
        self.user.refresh_from_db()
        self.assertTrue(self.profile.email_verified)
        self.assertFalse(self.user.is_active)

    def test_validate_email_rejects_invalid_token(self):
        response = self.client.get("/validate-email/", data={"token": "bad-token"})

        self.assertEqual(response.status_code, 400)

        self.profile.refresh_from_db()
        self.assertFalse(self.profile.email_verified)
