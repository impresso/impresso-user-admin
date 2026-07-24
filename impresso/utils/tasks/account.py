import logging
import smtplib
from logging import Logger
from django.contrib.auth.models import User, Group
from django.core import signing
from django.utils.http import urlencode

from impresso.utils.tasks.email import send_templated_email_with_context
from ...models import UserChangePlanRequest
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

default_logger = logging.getLogger(__name__)
# Salt used by Django signing to scope email-validation tokens. Changing it
# invalidates previously issued validation links.
EMAIL_VALIDATION_SALT = "impresso.email_validation"


def getEmailsContents(prefix: str, context: dict) -> tuple[str, str]:
    """
    Renders email contents in both text and HTML formats.

    Args:
        prefix (str): The prefix used to identify the email template files.
        context (dict): The context dictionary to be used for rendering the templates.

    Returns:
        tuple[str, str]: A tuple containing the rendered text content and HTML content.
    """
    txt_content = render_to_string(f"emails/{prefix}.txt", context=context)
    html_content = render_to_string(f"emails/{prefix}.html", context=context)
    return txt_content, html_content


def build_email_validation_token(user: User) -> str:
    """Build a signed token used to validate a newly registered email address."""
    return signing.dumps(
        {"user_id": user.pk, "email": user.email},
        salt=EMAIL_VALIDATION_SALT,
    )


def build_email_validation_link(user: User) -> str:
    """Build the absolute email-validation URL for a newly registered user."""
    token = build_email_validation_token(user)
    return (
        f"{settings.IMPRESSO_BASE_URL}{reverse('validate-email')}?"
        f"{urlencode({'token': token})}"
    )


def send_emails_after_user_registration(user_id: int, logger=default_logger):
    """
    Sends a confirmation email to the user with the given user_id.
    At this stage, the user record in the database has already been created and assigned to
    user desired "plan" group (one of the settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS),
    but it is NOT ACTIVE. In parallel, staff receives a message via email
    (to settings.DEFAULT_FROM_EMAIL)

    Args:
        user_id (int): The ID of the user to send the password reset email to.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.

    Raises:
        User.DoesNotExist: If no active user with the given user_id is found.
        Exception: If there is an error sending the email.
    """
    logger.info(f"Send email to user={user_id}...")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.info(f"user={user_id} NOT FOUND!")
        raise

    groups_names = [g for g in user.groups.values_list("name", flat=True)]
    logger.info(f"user={user_id} active={user.is_active} groups_names={groups_names}")

    email_template_prefix = "account_created_mailto_user"
    email_subject = settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_REGISTRATION_PLAN_BASIC
    plan_label = settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL

    if settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER in groups_names:
        email_template_prefix = "account_created_mailto_researcher"
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL
        email_subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_REGISTRATION_PLAN_RESEARCHER
        )
    elif settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL in groups_names:
        email_template_prefix = "account_created_mailto_educational"
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL
        email_subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_REGISTRATION_PLAN_EDUCATIONAL
        )

    validation_link = build_email_validation_link(user)

    txt_content, html_content = getEmailsContents(
        prefix=email_template_prefix,
        context=(
            {
                "user": user,
                "plan_label": plan_label,
                "impresso_base_url": settings.IMPRESSO_BASE_URL,
                "validation_link": validation_link,
            }
        ),
    )
    email_being_sent_without_error = False
    try:
        emailMessage = EmailMultiAlternatives(
            subject=email_subject,
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                user.email,
            ],
            reply_to=[
                settings.DEFAULT_FROM_EMAIL,
            ],
        )
        emailMessage.attach_alternative(html_content, "text/html")
        emailMessage.send(fail_silently=False)
        email_being_sent_without_error = True
    except smtplib.SMTPException as e:
        logger.exception(f"SMTPException Error sending email: {e}")
    except Exception as e:
        logger.exception(f"Error sending email '{email_template_prefix}', error: {e}")
    logger.info(f"Email '{email_template_prefix}' succeffully sent to user={user_id}")

    # send email to staff
    logger.info(
        f"Send email to staff with plan={plan_label} for user={user_id} template={email_template_prefix}"
    )
    admin_url_to_handle_change_request = reverse(
        # admin/auth/user/123/change/
        "admin:user_toggle_status",
        args=[user.id],
    )
    absolute_admin_url_to_handle_change_request = (
        f"{settings.IMPRESSO_BASE_URL}{admin_url_to_handle_change_request}"
    )
    txt_content, html_content = getEmailsContents(
        prefix="account_created_mailto_staff",
        context=(
            {
                "user": user,
                "plan_label": plan_label,
                "email_being_sent_without_error": email_being_sent_without_error,
                "absolute_admin_url_to_handle_change_request": absolute_admin_url_to_handle_change_request,
            }
        ),
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject=f"Request: {email_subject}",
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                settings.DEFAULT_FROM_EMAIL,
            ],
            cc=[],
        )
        emailMessage.attach_alternative(html_content, "text/html")
        emailMessage.send(fail_silently=False)
        logger.info(
            f"user={user_id} Sending email to staff for plan change request generated from user"
        )
    except smtplib.SMTPException as e:
        logger.exception(
            f"user={user_id} SMTPException Error sending email: {e} to staff"
        )
    except Exception as e:
        logger.exception(f"user={user_id} Error sending email: {e} to staff")


def send_emails_after_user_activation(
    user_id: int, logger: Logger = default_logger
) -> None:
    logger.info(f"looking for user={user_id}...")
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.info(f"user={user_id} NOT FOUND!")
        raise

    groups_names = user.groups.values_list("name", flat=True)
    logger.info(f"user={user_id} active={user.is_active} groups={groups_names}")
    txt_content, html_content = getEmailsContents(
        prefix="account_activated_mailto_user",
        context=(
            {
                "user": user,
                "impresso_base_url": settings.IMPRESSO_BASE_URL,
            }
        ),
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject="Access granted to the Impresso interface",
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                user.email,
            ],
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


def send_emails_after_user_activation_plan_rejected(
    user_id: int, logger: Logger = default_logger
) -> None:
    """
    Sends a notification email to the user informing them that their activation
    has been processed, but they have been activated only on the BASIC plan.

    Args:
        user_id (int): The ID of the user to send the email to.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.
    Raises:
        User.DoesNotExist: If no user with the given user_id is found.
        Exception: If there is an error sending the email.
    """
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"user={user_id} NOT FOUND!")
        return
    send_templated_email_with_context(
        template="account_activated_plan_rejected_to_user",
        subject=settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_ACTIVATION_PLAN_REJECTED_TO_USER,
        context={
            "user": user,
            "impresso_base_url": settings.IMPRESSO_BASE_URL,
            "plan_label": settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL,
        },
        from_email=settings.IMPRESSO_EMAIL_LABEL_DEFAULT_FROM_EMAIL,
        to=[
            user.email,
        ],
        cc=[],
        reply_to=[
            settings.DEFAULT_FROM_EMAIL,
        ],
        logger=logger,
        fail_silently=False,
    )


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
            subject=settings.IMPRESSO_EMAIL_SUBJECT_PASSWORD_RESET,
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
    plan: str,
    logger: Logger = default_logger,
) -> None:
    """
    Sends the message to change plan to staff and a receipt email back to the sender with the given user_id.

    Args:
        user_id (int): The ID of the user that initiated the change plan request.".
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.

    Raises:
        User.DoesNotExist: If no active user with the given user_id is found.
        ValueError: If the plan is not in the available plans.
        Exception: If there is an error sending the email.
    """
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.error(f"user={user_id} NOT FOUND or is not active!")
        raise
    if plan not in settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS:
        logger.error(
            f"user={user_id} bad request, plan is not in {settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS}"
        )
        raise ValueError(
            f"plan={plan} is not in {settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS}"
        )
    # this suffix to get the right email template
    plan_template_suffix = "_basic"
    # label for the plan, plain string
    plan_label = settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL
    plan_group_name = settings.IMPRESSO_GROUP_USER_PLAN_BASIC

    if plan == settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER:
        plan_template_suffix = "_researcher"
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL
        plan_group_name = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER
    elif plan == settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL:
        plan_template_suffix = "_educational"
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL
        plan_group_name = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL
    # check if the user already belongs to the group, print out user groups to be 100% sure
    user_groups_names = [n for n in user.groups.values_list("name", flat=True)]
    # retrieve user current plan
    current_plan_label = settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL
    if settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER in user_groups_names:
        current_plan_label = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL
    elif settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL in user_groups_names:
        current_plan_label = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL

    logger.info(
        f"user={user_id} Checking if user already associated groups... groups={user_groups_names} ..."
    )

    if plan_group_name in user_groups_names:
        logger.info(
            f"user={user_id} already in the group={plan_group_name}, no need to change"
        )
        return

    # create the user change plan request in the DB
    plan_as_group = Group.objects.get(name=plan_group_name)
    logger.info(
        f"user={user_id} creating or updating related UserChangePlanRequest to {plan_group_name}"
    )

    change_plan_request, created = UserChangePlanRequest.objects.get_or_create(
        user=user,
        defaults={
            "plan": plan_as_group,
        },
    )
    if not created:
        change_plan_request.plan = plan_as_group
        change_plan_request.status = UserChangePlanRequest.STATUS_PENDING
        change_plan_request.save()

    logger.info(
        f"user={user_id} created={created} change_plan_request={change_plan_request}"
    )

    # email for the user as a receipt
    prefix = f"account_plan_change_to{plan_template_suffix}"
    logger.info(
        f"user={user_id} Sending email to staff and user={user_id} with plan={plan} template={prefix}"
    )

    txt_content, html_content = getEmailsContents(
        prefix=prefix,
        context=(
            {
                "user": user,
                "plan_to_name": plan_label,
                "current_plan_name": current_plan_label,
                "from_email": settings.DEFAULT_FROM_EMAIL,
            }
        ),
    )
    email_being_sent_without_error = False
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
        email_being_sent_without_error = True
        logger.info(f"Change plan request RECEPIT email sent to user={user_id}")
    except smtplib.SMTPException as e:
        logger.exception(f"SMTPException Error sending email: {e} to user={user_id}")
    except Exception as e:
        logger.exception(f"Error sending email: {e} to user={user_id}")

    # email for the staff
    prefix = f"account_plan_change_to_staff"
    logger.info(
        f"Sending email to staff with plan={plan} for user={user_id} template={prefix}"
    )
    admin_url_to_handle_change_request = reverse(
        "admin:impresso_userchangeplanrequest_change",
        args=[change_plan_request.id],
    )
    absolute_admin_url_to_handle_change_request = (
        f"{settings.IMPRESSO_BASE_URL}{admin_url_to_handle_change_request}"
    )

    txt_content, html_content = getEmailsContents(
        prefix=prefix,
        context=(
            {
                "user": user,
                "plan_to_name": plan_label,
                "current_plan_name": current_plan_label,
                "from_email": settings.DEFAULT_FROM_EMAIL,
                "email_being_sent_without_error": email_being_sent_without_error,
                "absolute_admin_url_to_handle_change_request": absolute_admin_url_to_handle_change_request,
            }
        ),
    )

    # send email to the staff
    try:
        emailMessage = EmailMultiAlternatives(
            subject=f"Plan Change Request from {user.username}",
            body=txt_content,
            from_email=f"Impresso Team <{settings.DEFAULT_FROM_EMAIL}>",
            to=[
                settings.DEFAULT_FROM_EMAIL,
            ],
            cc=[],
        )
        emailMessage.attach_alternative(html_content, "text/html")
        emailMessage.send(fail_silently=False)
        logger.info(
            f"user={user_id} Sending email to staff for plan change request generated from user"
        )
    except smtplib.SMTPException as e:
        logger.exception(
            f"user={user_id} SMTPException Error sending email: {e} to staff"
        )
    except Exception as e:
        logger.exception(f"user={user_id} Error sending email: {e} to staff")


def send_email_plan_change_accepted(
    user_id: int,
    plan: str,
    logger: Logger = default_logger,
) -> None:
    """
    Sends the message that plan has changed to the requester user as email receipt given user_id.

    Args:
        user_id (int): The ID of the user that initiated the change plan request.".
        plan (None): The plan that was accepted.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.
    Raises:
        User.DoesNotExist: If no active user with the given user_id is found (or they have been disabled in the meanwhile)
        Exception: If there is an error sending the email.
    """
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.error(f"user={user_id} NOT FOUND or is not active!")
        raise

    if plan not in settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS:
        logger.error(
            f"user={user_id} bad request, plan is not in {settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS}"
        )
        raise ValueError(
            f"plan={plan} is not in {settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS}"
        )

    plan_label = settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL

    if plan == settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER:
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL
    elif plan == settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL:
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL

    prefix = f"account_plan_change_accepted"
    logger.info(
        f"user={user_id} Sending email to user={user_id} with plan={plan} template={prefix}"
    )

    txt_content, html_content = getEmailsContents(
        prefix=prefix,
        context=(
            {
                "user": user,
                "plan_to_name": plan_label,
                "from_email": settings.DEFAULT_FROM_EMAIL,
            }
        ),
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject="Your Subscription Plan Change is Confirmed",
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
        logger.info(f"Plan change acceptance email sent to user={user_id}")
    except smtplib.SMTPException as e:
        logger.exception(f"SMTPException Error sending email: {e} to user={user_id}")
    except Exception as e:
        logger.exception(f"Error sending email: {e} to user={user_id}")


def send_magic_link_email(
    user_id: int,
    token: str,
    magic_link_callback_url: str = "https://dev.impresso-project.ch/institutions-access/magic-link",
    logger: Logger = default_logger,
) -> None:
    """
    Sends a magic link email to the user with the given user_id.

    The magic link is constructed by appending the token as a query parameter
    to the callback URL: {magic_link_callback_url}?token={token}

    Args:
        user_id (int): The ID of the user to send the magic link email to.
        token (str): The token to include in the magic link URL.
        magic_link_callback_url (str, optional): The base URL for the magic link.
            Defaults to "https://dev.impresso-project.ch/institutions-access/magic-link".
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.

    Raises:
        User.DoesNotExist: If no active user with the given user_id is found.
        Exception: If there is an error sending the email.
    """
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.error(f"user={user_id} NOT FOUND or is not active!")
        raise

    from urllib.parse import urlencode

    magic_link = f"{magic_link_callback_url}?{urlencode({'token': token})}"
    logger.info(f"[user:{user_id}] Sending magic link email...")
    send_templated_email_with_context(
        template="account_magic_link",
        subject="Your Impresso access link",
        context={
            "user": user,
            "magic_link": magic_link,
        },
        from_email=settings.IMPRESSO_EMAIL_LABEL_DEFAULT_FROM_EMAIL,
        to=[user.email],
        cc=[],
        reply_to=[settings.DEFAULT_FROM_EMAIL],
        logger=logger,
        fail_silently=False,
    )
    logger.info(f"[user:{user_id}] Magic link email sent.")


def send_email_plan_change_rejected(
    user_id: int,
    plan: str,
    logger: Logger = default_logger,
) -> None:
    """
    Sends the message that plan change has been rejected to the requester user as email receipt given user_id.

    Args:
        user_id (int): The ID of the user that initiated the change plan request.
        plan (str): The plan that was rejected.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.

    Raises:
        User.DoesNotExist: If no active user with the given user_id is found (or they have been disabled in the meanwhile).
        ValueError: If the plan is not in the available plans.
        Exception: If there is an error sending the email.
    """
    try:
        user = User.objects.get(pk=user_id, is_active=True)
    except User.DoesNotExist:
        logger.error(f"user={user_id} NOT FOUND or is not active!")
        raise

    if plan not in settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS:
        logger.error(
            f"user={user_id} bad request, plan is not in {settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS}"
        )
        raise ValueError(
            f"plan={plan} is not in {settings.IMPRESSO_GROUP_USERS_AVAILABLE_PLANS}"
        )

    plan_label = settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL

    if plan == settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER:
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL
    elif plan == settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL:
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL

    prefix = f"account_plan_change_rejected"
    logger.info(
        f"user={user_id} Sending email to user={user_id} with plan={plan} template={prefix}"
    )

    txt_content, html_content = getEmailsContents(
        prefix=prefix,
        context=(
            {
                "user": user,
                "plan_to_name": plan_label,
                "from_email": settings.DEFAULT_FROM_EMAIL,
            }
        ),
    )
    try:
        emailMessage = EmailMultiAlternatives(
            subject="Your Subscription Plan Change Request is Rejected",
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
        logger.info(f"Plan change rejection email sent to user={user_id}")
    except smtplib.SMTPException as e:
        logger.exception(f"SMTPException Error sending email: {e} to user={user_id}")
    except Exception as e:
        logger.exception(f"Error sending email: {e} to user={user_id}")
