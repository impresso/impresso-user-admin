import logging
from logging import Logger
from django.conf import settings
from django.contrib.auth.models import User
from impresso.models.userBitmap import UserBitmap
from impresso.utils.tasks.email import send_templated_email_with_context
from impresso.models.userSpecialMembershipRequest import UserSpecialMembershipRequest

default_logger = logging.getLogger(__name__)


def apply_special_membership_to_bitmap(
    instance: UserSpecialMembershipRequest,
    created: bool,
    logger: Logger = default_logger,
) -> None:
    logger.info(
        f"apply_special_membership_to_bitmap for user={instance.user.pk} subscription={instance.subscription.title if instance.subscription else 'None'} status={instance.status}"
    )
    # Additional actions can be added here if needed when a UserSpecialMembershipRequest is saved.
    # get user bitmap of instance.user
    user_bitmap, created = UserBitmap.objects.get_or_create(user=instance.user)
    logger.info(
        f"User {instance.user.pk} has bitmap {bin(user_bitmap.get_bitmap_as_int())}, {'(just created)' if created else '(already existing)'}"
    )

    if instance.status == UserSpecialMembershipRequest.STATUS_APPROVED:
        user_bitmap.subscriptions.add(instance.subscription)

    elif instance.status in [
        UserSpecialMembershipRequest.STATUS_REJECTED,
        UserSpecialMembershipRequest.STATUS_PENDING,
    ]:
        user_bitmap.subscriptions.remove(instance.subscription)
        # this should update the bitmap thanks to the signal @m2m_changed update_user_bitmap


def send_email_after_user_special_membership_request_updated(
    instance: UserSpecialMembershipRequest,
    fail_silently: bool = False,
    logger: Logger = default_logger,
) -> None:
    """
    Sends an email to the user after a special membership request has been created.

    Args:
        instance (UserSpecialMembershipRequest): The UserSpecialMembershipRequest instance.
        fail_silently (bool, optional): Whether to fail silently if there is an error sending the email. Defaults to False.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.
    Raises:
        Exception: If there is an error sending the email.
    """
    if instance.status == UserSpecialMembershipRequest.STATUS_APPROVED:
        template = "user_special_membership_request_approved_to_user"
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_ACCEPTED_TO_USER
        )
    elif instance.status == UserSpecialMembershipRequest.STATUS_REJECTED:
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_REJECTED_TO_USER
        )
        template = "user_special_membership_request_rejected_to_user"
    else:
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_PENDING_TO_USER
        )
        template = "user_special_membership_request_pending_to_user"

    send_templated_email_with_context(
        template=template,
        subject=subject,
        context={
            "user": instance.user,
            "user_special_membership_request": instance,
        },
        from_email=settings.IMPRESSO_EMAIL_LABEL_DEFAULT_FROM_EMAIL,
        to=[
            instance.user.email,
        ],
        cc=[],
        reply_to=[
            settings.DEFAULT_FROM_EMAIL,
        ],
        logger=logger,
        fail_silently=fail_silently,
    )


def send_email_after_user_special_membership_request_created(
    instance: UserSpecialMembershipRequest,
    fail_silently: bool = False,
    logger: Logger = default_logger,
) -> None:
    """
    Sends an email to the user after a special membership request has been created.
    Also sends an email to the reviewer with reply-to set to the requester's
    email, enabling direct confidential exchange (e.g., to send contracts for signature).

    Args:
        instance (UserSpecialMembershipRequest): The UserSpecialMembershipRequest instance.
        fail_silently (bool, optional): Whether to fail silently if there is an error sending the email. Defaults to False.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.
    Raises:
        Exception: If there is an error sending the email.
    """
    send_templated_email_with_context(
        template="user_special_membership_request_to_user",
        subject=settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_USER,
        context={
            "user": instance.user,
            "user_special_membership_request": instance,
        },
        from_email=settings.IMPRESSO_EMAIL_LABEL_DEFAULT_FROM_EMAIL,
        to=[
            instance.user.email,
        ],
        cc=[],
        reply_to=[
            settings.DEFAULT_FROM_EMAIL,
        ],
        logger=logger,
        fail_silently=fail_silently,
    )

    # Also send an email to the reviewer
    reviewer = instance.reviewer or (
        instance.subscription.reviewer if instance.subscription else None
    )
    if reviewer and reviewer.email:
        send_templated_email_with_context(
            template="user_special_membership_request_pending_to_reviewer",
            subject=settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_PENDING_TO_REVIEWER,
            context={
                "reviewer": reviewer,
                "user": instance.user,
                "user_special_membership_request": instance,
            },
            from_email=settings.IMPRESSO_EMAIL_LABEL_DEFAULT_FROM_EMAIL,
            to=[
                reviewer.email,
            ],
            reply_to=[
                instance.user.email,
            ],
            logger=logger,
            fail_silently=fail_silently,
        )
    else:
        logger.warning(
            f"No reviewer with email found for special membership request {instance.pk}, "
            "skipping reviewer notification."
        )
