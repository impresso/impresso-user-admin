from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from impresso.models import Profile
from impresso.signals import create_default_groups


class TestCreateAccountCommand(TestCase):
    """Test account creation through the createaccount management command."""

    def setUp(self) -> None:
        create_default_groups(sender="impresso")

    @patch("builtins.input", return_value="y")
    def test_complete_populates_names_and_random_profile_pattern(
        self, mock_input: object
    ) -> None:
        output = StringIO()

        call_command(
            "createaccount",
            "jane-doe@example.com",
            "--complete",
            stdout=output,
        )

        user = User.objects.get(username="jane-doe")
        profile = Profile.objects.get(user=user)
        self.assertEqual(user.first_name, "jane")
        self.assertEqual(user.last_name, "doe")
        self.assertEqual(profile.displayname, "jane doe")
        self.assertRegex(profile.pattern, r"^(#[0-9a-f]{6},){4}#[0-9a-f]{6}$")

    @patch("builtins.input", return_value="y")
    def test_adds_profile_affiliation_and_institutional_url(
        self, mock_input: object
    ) -> None:
        call_command(
            "createaccount",
            "jane-doe@example.com",
            "--affiliation",
            "University of Example",
            "--institutional_url",
            "https://example.edu",
            stdout=StringIO(),
        )

        profile = Profile.objects.get(user__username="jane-doe")
        self.assertEqual(profile.affiliation, "University of Example")
        self.assertEqual(profile.institutional_url, "https://example.edu")

    @patch("builtins.input", return_value="y")
    def test_complete_defaults_to_false(self, mock_input: object) -> None:
        call_command("createaccount", "jane-doe@example.com", stdout=StringIO())

        user = User.objects.get(username="jane-doe")
        self.assertEqual(user.first_name, "")
        self.assertEqual(user.last_name, "")
