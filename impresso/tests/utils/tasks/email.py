"""
Test cases for the Django email utilities module.
"""

from django.test import TestCase
from django.core import mail
from django.core.exceptions import ValidationError

from django.contrib.auth import get_user_model
from unittest.mock import patch
import smtplib


User = get_user_model()
# Import your email utilities - adjust the import path to match your project structure
# For example, if the module is in yourapp/utils/email_utils.py:
# from yourapp.utils.email_utils import (
#     send_templated_email_with_context,
#     get_emails_rendered_contents,
#     validate_email_addresses,
# )

# For this test, we'll assume the functions are imported correctly
# Replace 'your_module_path' with the actual path
from impresso.utils.tasks.email import (
    send_templated_email_with_context,
    get_emails_rendered_contents,
    validate_email_addresses,
)


class EmailUtilsTestCase(TestCase):
    """Test case for email utility functions."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a test user
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass123"
        )

        # Common email parameters
        self.from_email = "noreply@example.com"
        self.to_emails = ["recipient@example.com"]
        self.to_wrong_emails = ["invalid-email"]
        self.subject = "Test Email Subject"

        # Email context
        self.context = {
            "user": self.user,
            "username": self.user.username,
            "site_name": "Test Site",
        }

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_templated_email_success(self, mock_render):
        """Test successful email sending with templates."""
        mock_render.side_effect = [
            "Plain text content for {{ username }}",
            "<html>HTML content for {{ username }}</html>",
        ]

        result = send_templated_email_with_context(
            template="welcome",
            subject=self.subject,
            from_email=self.from_email,
            to=self.to_emails,
            context=self.context,
        )

        # Assert email was sent successfully
        self.assertTrue(result)

        # Check that one email was sent
        self.assertEqual(len(mail.outbox), 1)

        # Verify email details
        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.subject, self.subject)
        self.assertEqual(sent_email.from_email, self.from_email)
        self.assertEqual(sent_email.to, self.to_emails)

        # Verify both text and HTML versions exist
        self.assertIn("Plain text content", sent_email.body)
        self.assertEqual(len(sent_email.alternatives), 1)
        self.assertEqual(sent_email.alternatives[0][1], "text/html")

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_with_cc_bcc_reply_to(self, mock_render):
        """Test email with CC, BCC, and Reply-To addresses."""
        mock_render.side_effect = ["Text", "HTML"]

        cc_emails = ["cc@example.com"]
        bcc_emails = ["bcc@example.com"]
        reply_to_emails = ["reply@example.com"]

        result = send_templated_email_with_context(
            template="notification",
            subject=self.subject,
            from_email=self.from_email,
            to=self.to_emails,
            cc=cc_emails,
            bcc=bcc_emails,
            reply_to=reply_to_emails,
            context=self.context,
        )

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.cc, cc_emails)
        self.assertEqual(sent_email.bcc, bcc_emails)
        self.assertEqual(sent_email.reply_to, reply_to_emails)

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_with_attachments(self, mock_render):
        """Test email with file attachments."""
        mock_render.side_effect = ["Text", "HTML"]

        pdf_content = b"%PDF-1.4 fake pdf content"
        attachments = [
            ("report.pdf", pdf_content, "application/pdf"),
        ]

        result = send_templated_email_with_context(
            template="report",
            subject=self.subject,
            from_email=self.from_email,
            to=self.to_emails,
            context=self.context,
            attachments=attachments,
        )

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertEqual(len(sent_email.attachments), 1)
        self.assertEqual(sent_email.attachments[0][0], "report.pdf")

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_empty_recipients(self, mock_render):
        """Test that empty recipient list raises ValueError."""
        mock_render.side_effect = ["Text", "HTML"]

        with self.assertRaises(ValueError) as context:
            send_templated_email_with_context(
                template="test",
                subject=self.subject,
                from_email=self.from_email,
                to=[],  # Empty recipient list
                context=self.context,
            )

        self.assertIn("cannot be empty", str(context.exception))

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_invalid_email_address(self, mock_render):
        """Test that invalid email addresses raise ValidationError."""
        mock_render.side_effect = ["Text", "HTML"]

        with self.assertRaises(ValidationError):
            send_templated_email_with_context(
                template="test",
                subject=self.subject,
                from_email=self.from_email,  # Invalid format
                to=self.to_wrong_emails,
                context=self.context,
            )

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_fail_silently(self, mock_render):
        """Test fail_silently parameter returns False on error."""
        mock_render.side_effect = ["Text", "HTML"]

        # Test with empty recipients and fail_silently=True
        result = send_templated_email_with_context(
            template="test",
            subject=self.subject,
            from_email=self.from_email,
            to=[],
            context=self.context,
            fail_silently=True,
        )

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    @patch("django.core.mail.EmailMultiAlternatives.send")
    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_smtp_error(self, mock_render, mock_send):
        """Test handling of SMTP errors."""
        mock_render.side_effect = ["Text", "HTML"]
        mock_send.side_effect = smtplib.SMTPException("SMTP server error")

        with self.assertRaises(smtplib.SMTPException):
            send_templated_email_with_context(
                template="test",
                subject=self.subject,
                from_email=self.from_email,
                to=self.to_emails,
                context=self.context,
            )

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_template_rendering_error(self, mock_render):
        """Test handling of template rendering errors."""
        mock_render.side_effect = Exception("Template not found")

        with self.assertRaises(RuntimeError) as context:
            send_templated_email_with_context(
                template="nonexistent",
                subject=self.subject,
                from_email=self.from_email,
                to=self.to_emails,
                context=self.context,
            )

        self.assertIn("Failed to render", str(context.exception))

    def test_validate_email_addresses_valid(self):
        """Test validation of valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
            "admin+tag@example.com",
        ]

        # Should not raise any exception
        try:
            validate_email_addresses(valid_emails)
        except ValidationError:
            self.fail("validate_email_addresses raised ValidationError unexpectedly")

    def test_validate_email_addresses_invalid(self):
        """Test validation catches invalid email addresses."""
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user @example.com",
        ]

        for invalid_email in invalid_emails:
            with self.assertRaises(ValidationError):
                validate_email_addresses([invalid_email])

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_get_emails_rendered_contents(self, mock_render):
        """Test template rendering function."""
        mock_render.side_effect = [
            "Plain text: {{ username }}",
            "<html>HTML: {{ username }}</html>",
        ]

        txt_content, html_content = get_emails_rendered_contents(
            prefix="test_template", context={"username": "testuser"}
        )

        self.assertIn("Plain text", txt_content)
        self.assertIn("<html>HTML", html_content)

        # Verify render_to_string was called with correct paths
        self.assertEqual(mock_render.call_count, 2)
        calls = mock_render.call_args_list
        self.assertEqual(calls[0][0][0], "emails/test_template.txt")
        self.assertEqual(calls[1][0][0], "emails/test_template.html")

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_custom_template_directory(self, mock_render):
        """Test using custom template directory."""
        mock_render.side_effect = ["Text", "HTML"]

        get_emails_rendered_contents(
            prefix="custom", context={}, template_dir="custom_emails"
        )

        calls = mock_render.call_args_list
        self.assertEqual(calls[0][0][0], "custom_emails/custom.txt")
        self.assertEqual(calls[1][0][0], "custom_emails/custom.html")

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_context_defaults_to_empty_dict(self, mock_render):
        """Test that context parameter defaults properly to empty dict."""
        mock_render.side_effect = ["Text", "HTML"]

        result = send_templated_email_with_context(
            template="test",
            subject=self.subject,
            from_email=self.from_email,
            to=self.to_emails,
            # No context provided
        )

        self.assertTrue(result)
        # Verify render_to_string was called with empty context
        calls = mock_render.call_args_list
        self.assertEqual(calls[0][1]["context"], {})

    @patch("impresso.utils.tasks.email.render_to_string")
    def test_send_email_none_optional_parameters(self, mock_render):
        """Test that None values for optional parameters are handled correctly."""
        mock_render.side_effect = ["Text", "HTML"]

        result = send_templated_email_with_context(
            template="test",
            subject=self.subject,
            from_email=self.from_email,
            to=self.to_emails,
            cc=None,
            bcc=None,
            reply_to=None,
            context=None,
            attachments=None,
        )

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)

        sent_email = mail.outbox[0]
        self.assertEqual(sent_email.cc, [])
        self.assertEqual(sent_email.bcc, [])
        self.assertEqual(sent_email.reply_to, [])
