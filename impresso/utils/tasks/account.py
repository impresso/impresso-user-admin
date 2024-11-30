import logging
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
    user_id,
    token="token",
    callback_url="https://impresso-project.ch/app/reset-password",
    logger=default_logger,
):
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
