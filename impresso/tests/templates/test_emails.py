"""
Test that all email templates in impresso/templates/emails/ render without
raising runtime errors.

ENV=test pipenv run ./manage.py test impresso.tests.templates.test_emails
"""

import logging
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.template import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.test import TestCase
from django.utils import timezone

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest

logger = logging.getLogger("console")

EMAILS_TEMPLATE_DIR = Path(settings.BASE_DIR) / "impresso" / "templates" / "emails"


class TestEmailTemplatesRenderable(TestCase):
    """
    Ensure every template under templates/emails/ can be parsed and rendered
    without raising a runtime error, using a context covering all variables
    referenced across the existing templates.

    ENV=test pipenv run ./manage.py test impresso.tests.templates.test_emails.TestEmailTemplatesRenderable
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="jane.doe",
            first_name="Jane",
            last_name="Doe",
            email="jane.doe@example.com",
            password="testpass123",
        )
        self.reviewer = User.objects.create_user(
            username="reviewer",
            first_name="Rick",
            last_name="Reviewer",
            email="reviewer@example.com",
            password="testpass123",
        )

        self.subscription = SpecialMembershipDataset.objects.create(
            title="Historical Newspapers Collection",
            bitmap_position=1,
        )

        self.membership_request = UserSpecialMembershipRequest.objects.create(
            user=self.user,
            reviewer=self.reviewer,
            subscription=self.subscription,
            temporary_expires_at=timezone.now(),
        )

        # Superset context of all variables used across the email templates.
        self.context = {
            "user": self.user,
            "reviewer": self.reviewer,
            "user_special_membership_request": self.membership_request,
            "user_special_membership_request_duration": "30 days",
            "latest_requests": [self.membership_request],
            "total_count": 3,
            "count_latest_requests": 1,
            "plan_to_name": "Researcher",
            "plan_label": "Researcher",
            "number_of_special_memberships": 2,
            "email_being_sent_without_error": True,
            "impresso_base_url": "https://impresso-project.ch",
        }

    def _get_template_prefixes(self) -> set[str]:
        """Return the unique template name prefixes found in the emails folder."""
        return {path.stem for path in EMAILS_TEMPLATE_DIR.glob("*.*")}

    def test_templates_folder_is_not_empty(self):
        prefixes = self._get_template_prefixes()
        self.assertTrue(prefixes, "No email templates found to test")

    def test_all_email_templates_render_without_errors(self):
        """Render every emails/<prefix>.txt and emails/<prefix>.html template."""
        prefixes = self._get_template_prefixes()

        for prefix in sorted(prefixes):
            for extension in ("txt", "html"):
                template_name = f"emails/{prefix}.{extension}"
                with self.subTest(template=template_name):
                    try:
                        rendered = render_to_string(
                            template_name, context=self.context
                        )
                    except (TemplateDoesNotExist, TemplateSyntaxError) as error:
                        self.fail(
                            f"Template {template_name} failed to parse/render: {error}"
                        )
                    self.assertIsInstance(rendered, str)
