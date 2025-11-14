import logging
from logging import Logger
from django.conf import settings
from django.contrib.auth.models import User
from impresso.utils.tasks.email import send_templated_email_with_context
from impresso.models.userSpecialMembershipRequest import UserSpecialMembershipRequest

default_logger = logging.getLogger(__name__)


def send_email_after_user_special_membership_request_created(
    user_id: int,
    user_special_membership_request_id: int,
    logger: Logger = default_logger,
) -> None:
    """
    Sends an email to the user after a special membership request has been created.

    Args:
        user_id (int): The ID of the user that initiated the change plan request.".
        user_special_membership_request_id (int): The ID of the UserSpecialMembershipRequest instance.
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

    try:
        user_special_membership_request = UserSpecialMembershipRequest.objects.get(
            pk=user_special_membership_request_id
        )
    except UserSpecialMembershipRequest.DoesNotExist:
        logger.error(
            f"user_special_membership_request={user_special_membership_request_id} NOT FOUND!"
        )
        raise

    send_templated_email_with_context(
        template="user_special_membership_request_to_user",
        subject=settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_USER,
        context={
            "user": user,
            "user_special_membership_request": user_special_membership_request,
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
    )
