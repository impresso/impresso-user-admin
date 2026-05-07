from celery.utils.log import get_task_logger
from django.utils import timezone
from django.conf import settings
from ..celery import app
from ..models.userSpecialMembershipRequest import UserSpecialMembershipRequest
from impresso.utils.tasks.userSpecialMembershipRequest import (
    apply_special_membership_to_bitmap,
    send_email_after_user_special_membership_request_created,
    send_email_after_user_special_membership_request_updated,
)

logger = get_task_logger(__name__)


def _is_temporary_auto_accept_enabled(req: UserSpecialMembershipRequest) -> bool:
    if not req.subscription:
        return False
    return bool(req.subscription.metadata.get("enableTemporaryAutomaticAcceptance"))


def _is_modality_cc_reviewer_enabled(req: UserSpecialMembershipRequest) -> bool:
    if not req.subscription:
        return False
    return bool(
        req.subscription.metadata.get("modality")
        == settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
    )


def _get_revoke_after_days(req: UserSpecialMembershipRequest) -> float:
    """
    Always return a positive number of days from the request's subscription metadata.
    If they're wrong or missing, get the value from the default settings.IMPRESSO_SPECIAL_MEMBERSHIP_TEMPORARY_APPROVAL_DEFAULT_DAYS
    """
    req.refresh_from_db()  # ensure we have the latest subscription metadata
    DEFAULT_DAYS: float = (
        settings.IMPRESSO_SPECIAL_MEMBERSHIP_TEMPORARY_APPROVAL_DEFAULT_DAYS
    )
    if not req.subscription:
        logger.warning(
            f"[instance:{req.pk}] No subscription associated with the request, cannot get revokeAfterDays, using default {DEFAULT_DAYS} day(s)"
        )
        return DEFAULT_DAYS

    revoke_after_days = req.subscription.metadata.get("revokeAfterDays")
    if isinstance(revoke_after_days, (int, float)) and revoke_after_days > 0:
        return float(revoke_after_days)

    logger.warning(
        f"[instance:{req.pk}] revokeAfterDays is missing or invalid in subscription metadata (value={revoke_after_days}), using default {DEFAULT_DAYS} day(s)"
    )
    return DEFAULT_DAYS


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_special_membership_request_created(self, instance_id: int) -> None:
    """
    The special membership request (pk:{instance_id}) has already been created in the database.
    In Django Admin site, this task is scheduled when the `impresso.signals.post_save_user_special_membership_request` signal is triggered;
    in other backends, this task must be called manually using the backend Celery integration.
    Note that this task can be called with a status other than PENDING, thus triggering the
    `after_special_membership_request_updated` logic immediately and skipping the
    `send_email_after_user_special_membership_request_created` logic.
    Args:
        self: The task instance.
        instance_id (int): The ID of the UserSpecialMembershipRequest instance that was created.
    """
    try:
        req = UserSpecialMembershipRequest.objects.get(pk=instance_id)
    except UserSpecialMembershipRequest.DoesNotExist:
        logger.error(f"[UserSpecialMembershipRequest:{instance_id}] DoesNotExist :(")
        return
    logger.info(
        f"[UserSpecialMembershipRequest:{instance_id}] triggered signals after_special_membership_request_created, for user={req.user.username} subscription={req.subscription.title if req.subscription else 'None'} status={req.status}"
    )
    # If the request is pending and temporary auto-accept is enabled, approve it as temporary,
    # and let celery beat handle revocation after expiration.
    # instead of going through the regular pending flow.
    if (
        req.status == UserSpecialMembershipRequest.STATUS_PENDING
        and _is_temporary_auto_accept_enabled(req)
    ):
        # Always set an expires at date in case of temporary approval
        revoke_after_days = _get_revoke_after_days(req)
        req.status = UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY
        # add the temporary expiration date using the last modified date + revoke_after_days
        req.temporary_expires_at = req.calculate_temporary_expiration(revoke_after_days)
        req.save()
        logger.info(
            f"[instance:{instance_id}] auto-accepted as temporary for {revoke_after_days} day(s)"
        )
        # The save above triggers the update task via signal, which applies bitmap
        # and sends the temporary-approval email. Revocation is handled by celery beat.
        return

    # Apply special membership to bitmap before sending emails, so that the user gets the access as soon as they receive the email
    apply_special_membership_to_bitmap(instance=req, created=True, logger=logger)

    if req.status != UserSpecialMembershipRequest.STATUS_PENDING:
        logger.info(
            f"[instance:{instance_id}] created with status {req.status}, skipping created email and sending update email instead"
        )
        after_special_membership_request_updated.delay(instance_id=instance_id)
        return

    send_email_after_user_special_membership_request_created(
        instance=req, logger=logger
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_special_membership_request_updated(self, instance_id: int) -> None:
    """
    Send emails after a UserSpecialMembershipRequest is updated.
    This task doesn't change the status of the request, but only reacts to the change by sending the appropriate email notifications and applying the special membership to the bitmap.

    In Django Admin site, this task is scheduled when the `impresso.signals.post_save_user_special_membership_request` signal is triggered and the instance is not newly created (i.e., it's an update);
    in other backends, this task must be called manually using the backend Celery integration.

    If current status is "STATUS_APPROVED", congratulate the user with the details of the special membership granted.
    If current status is "STATUS_PENDING", notify the institution reviewer with the details of the request AND to the user that their request is pending review.
    If current status is "STATUS_REJECTED", notify the user that their request has been rejected.

    Args:
        self: The task instance.
        instance_id (int): The ID of the UserSpecialMembershipRequest instance that was updated.

    Returns:
        None
    """
    # get request
    try:
        req = UserSpecialMembershipRequest.objects.get(pk=instance_id)
    except UserSpecialMembershipRequest.DoesNotExist:
        logger.error(
            f"[instance:{instance_id}] UserSpecialMembershipRequest.DoesNotExist"
        )
        return
    logger.info(
        f"[instance:{instance_id}] after_special_membership_request_updated for user={req.user.username} subscription={req.subscription.title if req.subscription else 'None'} status={req.status}"
    )
    apply_special_membership_to_bitmap(instance=req, created=False, logger=logger)
    send_email_after_user_special_membership_request_updated(
        instance=req,
        logger=logger,
        is_modality_cc_reviewer_enabled=_is_modality_cc_reviewer_enabled(req),
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def revoke_special_membership_request(self, instance_id: int) -> None:
    """
    Revoke a temporary special membership request when its expiration date is reached.

    Args:
        self: The task instance.
        instance_id (int): The ID of the UserSpecialMembershipRequest instance.
    """
    try:
        req = UserSpecialMembershipRequest.objects.get(pk=instance_id)
    except UserSpecialMembershipRequest.DoesNotExist:
        logger.error(
            f"[instance:{instance_id}] Cannot revoke temporary access, request not found"
        )
        return

    if req.status != UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY:
        logger.info(
            f"[instance:{instance_id}] revocation skipped because status is {req.status}"
        )
        return

    req.status = UserSpecialMembershipRequest.STATUS_REVOKED
    req.save()
    # usual signals will take care of applying the bitmap changes and sending the email notification about revocation
    logger.info(
        f"[instance:{instance_id}] temporary membership revoked for user={req.user.pk}"
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def revoke_expired_temporary_memberships_beat(self) -> None:
    """
    Periodic task to revoke any STATUS_APPROVED_TEMPORARY memberships
    that have passed their temporary_expires_at date.
    """
    expired_requests = UserSpecialMembershipRequest.objects.filter(
        status=UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
        temporary_expires_at__lt=timezone.now(),
    )

    count = expired_requests.count()
    if count == 0:
        logger.info("No expired temporary memberships found to revoke.")
        return

    logger.info(f"Found {count} expired temporary memberships to revoke.")

    for req in expired_requests:
        revoke_special_membership_request.delay(instance_id=req.pk)
