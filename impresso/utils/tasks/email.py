"""
Django Email Utilities Module

This module provides utility functions for rendering and sending templated emails
using Django's email framework. It supports both text and HTML email formats
with proper error handling and logging.

Example:
    Basic usage:
        >>> success = send_templated_email_with_context(
        ...     template='welcome',
        ...     subject='Welcome to Our Site',
        ...     from_email='noreply@example.com',
        ...     to=['user@example.com'],
        ...     context={'username': 'John'}
        ... )
"""

import logging
import smtplib
from logging import Logger
from typing import Optional

from django.core.mail import EmailMultiAlternatives, BadHeaderError
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


# Module-level logger
default_logger = logging.getLogger(__name__)

# Constants
DEFAULT_TEMPLATE_DIR = "emails"


def get_emails_rendered_contents(
    prefix: str,
    context: Optional[dict] = None,
    template_dir: str = DEFAULT_TEMPLATE_DIR,
) -> tuple[str, str]:
    """
    Renders email contents in both text and HTML formats from templates.

    This function loads Django templates and renders them with the provided context.
    It expects two template files to exist:
    - {template_dir}/{prefix}.txt for plain text version
    - {template_dir}/{prefix}.html for HTML version

    Args:
        prefix: The prefix/name used to identify the email template files.
            Templates should be named as '{prefix}.txt' and '{prefix}.html'.
        context: The context dictionary to be used for rendering the templates.
            Defaults to an empty dict if None is provided.
        template_dir: The directory where email templates are stored.
            Defaults to 'emails'.

    Returns:
        A tuple containing (text_content, html_content) where both are
        rendered strings ready to be used in an email.

    Raises:
        TemplateDoesNotExist: If either the .txt or .html template file
            cannot be found.
        TemplateSyntaxError: If there's a syntax error in the templates.

    Example:
        >>> txt, html = get_emails_rendered_contents(
        ...     prefix='welcome',
        ...     context={'user_name': 'John Doe'}
        ... )
    """
    if context is None:
        context = {}

    txt_content = render_to_string(f"{template_dir}/{prefix}.txt", context=context)
    html_content = render_to_string(f"{template_dir}/{prefix}.html", context=context)

    return txt_content, html_content


def validate_email_addresses(emails: list[str]) -> None:
    """
    Validates a list of email addresses.

    Args:
        emails: List of email addresses to validate.

    Raises:
        ValidationError: If any email address is invalid.
    """
    for email in emails:
        validate_email(email)


def send_templated_email_with_context(
    template: str,
    subject: str,
    from_email: str,
    to: list[str],
    cc: Optional[list[str]] = None,
    bcc: Optional[list[str]] = None,
    reply_to: Optional[list[str]] = None,
    context: Optional[dict] = None,
    attachments: Optional[list[tuple[str, bytes, str]]] = None,
    template_dir: str = DEFAULT_TEMPLATE_DIR,
    logger: Logger = default_logger,
    fail_silently: bool = False,
) -> bool:
    """
    Renders and sends a templated email with both text and HTML versions.

    This function loads email templates, renders them with the provided context,
    and sends the email using Django's EmailMultiAlternatives. It handles both
    plain text and HTML versions of the email.

    Args:
        template: The template prefix/name (without extension). Templates should
            exist as '{template}.txt' and '{template}.html' in the template directory.
        subject: The email subject line.
        from_email: The sender's email address.
        to: List of recipient email addresses. Must contain at least one address.
        cc: List of CC (carbon copy) recipient email addresses. Defaults to empty list.
        bcc: List of BCC (blind carbon copy) recipient email addresses. Defaults to empty list.
        reply_to: List of reply-to email addresses. Defaults to empty list.
        context: Dictionary of context variables to render in the templates.
            Defaults to an empty dict if None.
        attachments: List of attachments as tuples of (filename, content, mimetype).
            Example: [('report.pdf', pdf_bytes, 'application/pdf')]. Defaults to empty list.
        template_dir: Directory where email templates are stored. Defaults to 'emails'.
        logger: Logger instance to use for error logging. Defaults to module logger.
        fail_silently: If True, returns False on error instead of raising exception.
            Defaults to False.

    Returns:
        True if the email was sent successfully, False if an error occurred
        and fail_silently is True.

    Raises:
        ValidationError: If any email address is invalid (when fail_silently=False).
        smtplib.SMTPException: If SMTP-related sending fails (when fail_silently=False).
        ValueError: If the 'to' list is empty (when fail_silently=False).

    Example:
        >>> success = send_templated_email_with_context(
        ...     template='order_confirmation',
        ...     subject='Your Order #12345',
        ...     from_email='orders@example.com',
        ...     to=['customer@example.com'],
        ...     cc=['sales@example.com'],
        ...     reply_to=['support@example.com'],
        ...     context={
        ...         'order_number': '12345',
        ...         'customer_name': 'John Doe',
        ...         'total': 99.99
        ...     }
        ... )
    """
    # Handle None for context (mutable, so we need to check)
    if context is None:
        context = {}

    # Validate inputs
    if not to:
        error_msg = "The 'to' recipient list cannot be empty"
        logger.error(error_msg)
        if fail_silently:
            return False
        raise ValueError(error_msg)

    try:
        # Validate all email addresses
        validate_email_addresses(to)
        if cc:
            validate_email_addresses(cc)
        if bcc:
            validate_email_addresses(bcc)
        if reply_to:
            validate_email_addresses(reply_to)
    except ValidationError as e:
        logger.error(f"Invalid email address: {e}")
        if fail_silently:
            return False
        raise

    # Render email templates
    try:
        txt_content, html_content = get_emails_rendered_contents(
            prefix=template, context=context, template_dir=template_dir
        )
    except Exception as e:
        logger.error(f"Error rendering email template '{template}': {e}", exc_info=True)
        if fail_silently:
            return False
        raise RuntimeError(f"Failed to render email template: {e}") from e

    # Send email
    try:
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=txt_content,
            from_email=from_email,
            to=to,
            cc=cc or [],
            bcc=bcc or [],
            reply_to=reply_to or [],
        )

        # Attach HTML alternative
        email_message.attach_alternative(html_content, "text/html")

        # Add any attachments
        if attachments:
            for filename, content, mimetype in attachments:
                email_message.attach(filename, content, mimetype)

        email_message.send(fail_silently=False)

        logger.info(
            f"Email sent successfully - Subject: '{subject}', To: {to}, "
            f"CC: {cc or []}, BCC: {len(bcc) if bcc else 0} recipients"
        )
        return True

    except smtplib.SMTPException as e:
        logger.error(
            f"SMTP error sending email - To: {to}, Subject: '{subject}', "
            f"Error: {e}",
            exc_info=True,
        )
        if fail_silently:
            return False
        raise smtplib.SMTPException(f"SMTP error: {e}") from e

    except Exception as e:
        logger.error(
            f"Unexpected error sending email - To: {to}, Subject: '{subject}', "
            f"Error: {e}",
            exc_info=True,
        )
        if fail_silently:
            return False
        raise
