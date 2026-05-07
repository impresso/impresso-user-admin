import logging
from logging import Logger
from django.conf import settings
from impresso.models.userBitmap import UserBitmap
from impresso.utils.models.user import (
    get_number_of_special_memberships,
    get_plan_from_user_groups,
)
from impresso.utils.tasks.email import send_templated_email_with_context
from impresso.models.userSpecialMembershipRequest import UserSpecialMembershipRequest

default_logger = logging.getLogger(__name__)


def apply_special_membership_to_bitmap(
    instance: UserSpecialMembershipRequest,
    created: bool,
    logger: Logger = default_logger,
) -> None:
    """
    Applies the special membership to the user's bitmap based on the status of the
    UserSpecialMembershipRequest instance.

    Approved statuses add the subscription to the bitmap; non-approved statuses
    remove it.
    Args:
        instance (UserSpecialMembershipRequest): The UserSpecialMembershipRequest instance.
        created (bool): A boolean indicating whether the instance was created or updated.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.
    """
    logger.info(
        f"apply_special_membership_to_bitmap for user={instance.user.pk} subscription={instance.subscription.title if instance.subscription else 'None'} status={instance.status}"
    )
    # Additional actions can be added here if needed when a UserSpecialMembershipRequest is saved.
    # get user bitmap of instance.user
    user_bitmap, created = UserBitmap.objects.get_or_create(user=instance.user)
    logger.info(
        f"User {instance.user.pk} has bitmap {bin(user_bitmap.get_bitmap_as_int())}, {'(just created)' if created else '(already existing)'}"
    )
    if not instance.subscription:
        logger.warning(
            f"UserSpecialMembershipRequest {instance.pk} has no subscription? skipping bitmap update."
        )
        return
    if instance.status in [
        UserSpecialMembershipRequest.STATUS_APPROVED,
        UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
    ]:
        user_bitmap.subscriptions.add(instance.subscription)

    elif instance.status in [
        UserSpecialMembershipRequest.STATUS_REJECTED,
        UserSpecialMembershipRequest.STATUS_PENDING,
        UserSpecialMembershipRequest.STATUS_REVOKED,
    ]:
        user_bitmap.subscriptions.remove(instance.subscription)
        # this should update the bitmap thanks to the signal @m2m_changed update_user_bitmap


def send_email_after_user_special_membership_request_updated(
    instance: UserSpecialMembershipRequest,
    fail_silently: bool = False,
    is_modality_cc_reviewer_enabled: bool = False,
    logger: Logger = default_logger,
) -> None:
    """
    Sends an email to the user after a special membership request has been created.

    Args:
        instance (UserSpecialMembershipRequest): The UserSpecialMembershipRequest instance.
        fail_silently (bool, optional): Whether to fail silently if there is an error sending the email. Defaults to False.

        is_modality_cc_reviewer_enabled (bool, optional): Whether the modality for CC reviewers is enabled. Defaults to False.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.
    Raises:
        Exception: If there is an error sending the email.
    """
    reply_to = []
    plan_label, plan_group = get_plan_from_user_groups(instance.user)
    duration = None
    if instance.temporary_expires_at:
        delta = instance.temporary_expires_at - instance.date_created
        total_hours = int(delta.total_seconds() // 3600)
        if total_hours < 24:
            duration = f"{total_hours} hour{'s' if total_hours != 1 else ''}"
        else:
            total_days = int(delta.total_seconds() // 86400)
            duration = f"{total_days} day{'s' if total_days != 1 else ''}"
    if is_modality_cc_reviewer_enabled:
        reviewer = instance.reviewer or (
            instance.subscription.reviewer if instance.subscription else None
        )
        if reviewer and reviewer.email:
            reply_to.append(reviewer.email)
    if instance.status == UserSpecialMembershipRequest.STATUS_APPROVED:
        template = "user_special_membership_request_approved_to_user"
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_ACCEPTED_TO_USER
        )
    elif instance.status == UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY:
        template = "user_special_membership_request_approved_temporary_to_user"
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_ACCEPTED_TEMPORARY_TO_USER
        )
    elif instance.status == UserSpecialMembershipRequest.STATUS_REJECTED:
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_REJECTED_TO_USER
        )
        template = "user_special_membership_request_rejected_to_user"
    elif instance.status == UserSpecialMembershipRequest.STATUS_REVOKED:
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_REVOKED_TO_USER
        )
        template = "user_special_membership_request_revoked_to_user"
    else:
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_PENDING_TO_USER
        )
        template = "user_special_membership_request_pending_to_user"

    status_label = dict(UserSpecialMembershipRequest.STATUS_CHOICES).get(
        instance.status, instance.status
    )
    send_templated_email_with_context(
        template=template,
        subject=subject,
        context={
            "user": instance.user,
            "user_special_membership_request": instance,
            "plan_label": plan_label,
            "plan_group": plan_group,
            "user_special_membership_request_duration": duration,
            "status_label": status_label,
        },
        from_email=settings.IMPRESSO_EMAIL_LABEL_DEFAULT_FROM_EMAIL,
        to=[
            instance.user.email,
        ],
        cc=[],
        reply_to=reply_to,
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
    There are two modalities available: CC_REVIEWER: the reviewer is CC'd in the email sent to the user, with a clear indication
    in the email content that the reviewer is CC'd; NOTIFY_REVIEWER: the reviewer receives a
    SEPARATE email notification about the new request, with reply-to set to the requester's email for direct
    confidential exchange.

    Args:
        instance (UserSpecialMembershipRequest): The UserSpecialMembershipRequest instance.
        fail_silently (bool, optional): Whether to fail silently if there is an error sending the email. Defaults to False.
        logger (Logger, optional): The logger to use for logging information. Defaults to default_logger.
    Raises:
        Exception: If there is an error sending the email.
    """
    template = "user_special_membership_request_created_to_user"
    subject = (
        settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_USER
    )
    cc = []
    reviewer = instance.reviewer or (
        instance.subscription.reviewer if instance.subscription else None
    )
    plan_label, plan_group = get_plan_from_user_groups(instance.user)
    number_of_special_memberships = get_number_of_special_memberships(instance.user)
    status_label = dict(UserSpecialMembershipRequest.STATUS_CHOICES).get(
        instance.status, instance.status
    )
    # Default to NOTIFY_REVIEWER unless dataset metadata explicitly enables CC_REVIEWER.
    modality = settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER
    if instance.subscription and instance.subscription.is_modality_cc_reviewer_enabled():
        modality = settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
    if (
        modality
        == settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
        and reviewer
        and reviewer.email
    ):
        template = "user_special_membership_request_created_to_user_cc_reviewer"
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_USER_CC_REVIEWER
        )
        if reviewer and reviewer.email:
            cc.append(reviewer.email)
        else:
            logger.warning(
                f"No reviewer with email found for special membership request {instance.pk}, "
                "skipping reviewer CC."
            )
    logger.info(
        f"send_email_after_user_special_membership_request_created for user={instance.user.pk} "
        f"subscription={instance.subscription.title if instance.subscription else 'None'} "
        f"reviewer={reviewer.pk if reviewer else 'None'} "
        f"modality={modality} (if reviewer email is not found, modality will be downgraded to NOTIFY_REVIEWER) "
        f"plan_label={plan_label} plan_group={plan_group}"
    )
    send_templated_email_with_context(
        template=template,
        subject=subject,
        context={
            "user": instance.user,
            "reviewer": reviewer,
            "user_special_membership_request": instance,
            "plan_label": plan_label,
            "plan_group": plan_group,
            "number_of_special_memberships": number_of_special_memberships,
            "status_label": status_label,
        },
        from_email=settings.IMPRESSO_EMAIL_LABEL_DEFAULT_FROM_EMAIL,
        to=[
            instance.user.email,
        ],
        cc=cc,
        reply_to=[
            settings.DEFAULT_FROM_EMAIL,
        ],
        logger=logger,
        fail_silently=fail_silently,
    )

    if (
        modality
        == settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER
        and reviewer
        and reviewer.email
    ):
        # Send a SEPARATE email to the reviewer, with reply-to set to the requester's email for direct confidential exchange.
        template = "user_special_membership_request_created_to_reviewer"
        subject = (
            settings.IMPRESSO_EMAIL_SUBJECT_AFTER_USER_SPECIAL_MEMBERSHIP_REQUEST_CREATED_TO_REVIEWER
        )

        send_templated_email_with_context(
            template=template,
            subject=subject,
            context={
                "reviewer": reviewer,
                "user": instance.user,
                "user_special_membership_request": instance,
                "plan_label": plan_label,
                "plan_group": plan_group,
                "status_label": status_label,
                "number_of_special_memberships": number_of_special_memberships,
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
    elif (
        modality
        == settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER
    ):
        logger.warning(
            f"No reviewer with email found for special membership request {instance.pk}, "
            "skipping reviewer notification."
        )
