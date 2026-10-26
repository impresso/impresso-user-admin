from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.management import CommandError, call_command
from django.test import TestCase


class TestChangeUserPasswordsCommand(TestCase):
    """Test the changeuserpasswords management command."""

    def setUp(self) -> None:
        self.user = User.objects.create_user(
            username="jane-doe",
            email="jane-doe@example.com",
            password="initial-password",
        )

    def _create_tsv(self, content: str) -> Path:
        file = NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".tsv", delete=False)
        self.addCleanup(Path(file.name).unlink, missing_ok=True)
        with file:
            file.write(content)
        return Path(file.name)

    @patch("builtins.input", return_value="y")
    def test_changes_password_after_confirmation(self, mock_input: MagicMock) -> None:
        tsv_file = self._create_tsv(
            "username\tpassword\njane-doe@example.com\tnew-password\n"
        )

        call_command("changeuserpasswords", tsv_file)

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("new-password"))

    @patch("builtins.input")
    def test_rejects_invalid_row_before_prompt(self, mock_input: MagicMock) -> None:
        tsv_file = self._create_tsv(
            "username\tpassword\njane-doe@example.com\tnew-password\ninvalid\tother\n"
        )

        with self.assertRaisesMessage(
            CommandError, "Line 3 has an invalid email address: 'invalid'."
        ):
            call_command("changeuserpasswords", tsv_file)

        mock_input.assert_not_called()
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("initial-password"))

    def test_rejects_header_with_extra_column(self) -> None:
        tsv_file = self._create_tsv("username\tpassword\textra\n")

        with self.assertRaisesMessage(
            CommandError, "TSV header must contain exactly: username<TAB>password."
        ):
            call_command("changeuserpasswords", tsv_file)

    @patch("builtins.input")
    def test_rejects_data_row_with_extra_column(self, mock_input: MagicMock) -> None:
        tsv_file = self._create_tsv(
            "username\tpassword\njane-doe@example.com\tnew-password\textra\n"
        )

        with self.assertRaisesMessage(
            CommandError, "Line 2 must contain exactly two columns."
        ):
            call_command("changeuserpasswords", tsv_file)

        mock_input.assert_not_called()

    def test_rejects_repeated_header(self) -> None:
        tsv_file = self._create_tsv(
            "username\tpassword\nusername\tpassword\n"
        )

        with self.assertRaisesMessage(CommandError, "Line 2 repeats the TSV header."):
            call_command("changeuserpasswords", tsv_file)

    @patch("builtins.input")
    def test_rejects_missing_user_before_prompt(self, mock_input: MagicMock) -> None:
        tsv_file = self._create_tsv(
            "username\tpassword\nmissing@example.com\tnew-password\n"
        )

        with self.assertRaisesMessage(
            CommandError,
            "Line 2: user with email 'missing@example.com' does not exist.",
        ):
            call_command("changeuserpasswords", tsv_file)

        mock_input.assert_not_called()
