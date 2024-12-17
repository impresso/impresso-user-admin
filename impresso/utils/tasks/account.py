import logging
import smtplib
from logging import Logger
from django.core import mail
from django.contrib.auth.models import User
from django_registration.backends.activation.views import RegistrationView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

default_logger = logging.getLogger(__name__)


def getEmailsContents(prefix, context):
    txt_content = render_to_string(f"emails/{prefix}.txt", context=context)
    html_content = render_to_string(f"emails/{prefix}.html", context=context)
    return txt_content, html_content


def send_emails_after_user_registration(user_id, logger=default_logger, test=False):
    logger.info(f"looking for user={user_id}...")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.info(f"user={user_id} NOT FOUND!")
        raise

    logger.info(f"user={user_id} active={user.is_active}")
    view = RegistrationView()
    key = view.get_activation_key(user)
    txt_content, html_content = getEmailsContents(
        prefix="account_created_mailto_user", context=({"user": user, "key": key})
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject="Access to the impresso interface",
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                user.email,
            ],
            cc=[
                settings.DEFAULT_FROM_EMAIL,
            ],
            reply_to=[
                settings.DEFAULT_FROM_EMAIL,
            ],
        )
        emailMessage.attach_alternative(html_content, "text/html")
        emailMessage.send(fail_silently=False)

    except Exception:
        raise
    try:
        first_message = mail.outbox[0]
        print(first_message.subject)
        print(first_message.body)
    except Exception:
        logger.info("It looks like the mail settings is not a TEST environment :)")
        pass
    # send email to the user to confirm the subscription


def send_emails_after_user_activation(user_id, logger=default_logger):
    logger.info(f"looking for user={user_id}...")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.info(f"user={user_id} NOT FOUND!")
        raise
    logger.info(f"user={user_id} active={user.is_active}")
    txt_content, html_content = getEmailsContents(
        prefix="account_activated_mailto_user",
        context=(
            {
                "user": user,
            }
        ),
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject="Access granted to the impresso interface",
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                user.email,
            ],
            # cc=[
            #     settings.DEFAULT_FROM_EMAIL,
            # ],
            reply_to=[
                settings.DEFAULT_FROM_EMAIL,
            ],
        )
        emailMessage.attach_alternative(html_content, "text/html")
        emailMessage.send(fail_silently=False)

    except Exception:
        raise
    try:
        first_message = mail.outbox[0]
        logger.info("READING email in THE FAKE OUTBOX:")
        print(first_message.subject)
        print(first_message.body)
    except Exception:
        logger.info("It looks like the mail settings is not a TEST environment :)")
        pass


def send_email_password_reset(
    user_id: int,
    token: str = "token",
    callback_url: str = "https://impresso-project.ch/app/reset-password",
    logger: Logger = default_logger,
) -> None:
    """
    Sends a password reset email to the user with the given user_id.

    Args:
        user_id (int): The ID of the user to send the password reset email to.
        token (str, optional): The token to include in the password reset link. Defaults to "token".
        callback_url (str, optional): The URL to use for the password reset link. Defaults to "https://impresso-project.ch/app/reset-password".
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.

    Raises:
        User.DoesNotExist: If no active user with the given user_id is found.
        Exception: If there is an error sending the email.
    """
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.info(f"user={user_id} NOT FOUND!")
        raise
    txt_content, html_content = getEmailsContents(
        prefix="account_password_reset",
        context=(
            {"user": user, "token": token, "resetLink": f"{callback_url}/{token}"}
        ),
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject="Reset password for impresso",
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                user.email,
            ],
            cc=[],
            reply_to=[
                settings.DEFAULT_FROM_EMAIL,
            ],
        )
        emailMessage.attach_alternative(html_content, "text/html")
        emailMessage.send(fail_silently=False)
    except smtplib.SMTPException as e:
        logger.exception(f"SMTPException Error sending email: {e}")
    except Exception as e:
        logger.exception(f"Error sending email: {e}")
    logger.info(f"Password reset email sent to user={user_id}")


def send_email_plan_change(
    user_id: int,
    plan: None,
    callback_url: str = "https://impresso-project.ch/app/reset-password",
    logger: Logger = default_logger,
) -> None:
    """
    Sends the message to change plan to staff and a receipt email back to the sender with the given user_id.

    Args:
        user_id (int): The ID of the user that initiated the change plan request.".
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.

    Raises:
        User.DoesNotExist: If no active user with the given user_id is found.
        Exception: If there is an error sending the email.
    """
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.exception(f"user={user_id} NOT FOUND!")
        raise
    if plan not in settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS:
        logger.error(
            f"bad request, plan is not in {settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS}"
        )
        return
    # this suffix
    plan_suffix = settings.IMPRESSO_GROUP_USER_PLAN_BASIC

    if plan == settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER:
        plan_suffix = "plan_researcher"
    elif plan == settings.IMPRESSO_GROUP_USER_PLAN_EDUCTIONAL:
        plan_suffix = "plan_educational"

    txt_content, html_content = getEmailsContents(
        prefix=f"account_plan_change_to_{plan_suffix}",
        context=({"user": user}),
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject="Change plan for Impresso",
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                user.email,
            ],
            cc=[],
            reply_to=[
                settings.DEFAULT_FROM_EMAIL,
            ],
        )
        emailMessage.attach_alternative(html_content, "text/html")
        emailMessage.send(fail_silently=False)
    except smtplib.SMTPException as e:
        logger.exception(f"SMTPException Error sending email: {e}")
    except Exception as e:
        logger.exception(f"Error sending email: {e}")
    logger.info(f"Password reset email sent to user={user_id}")
