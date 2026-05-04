from datetime import timedelta

from celery.utils.log import get_task_logger
from django.utils import timezone

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


def _get_revoke_after_days(req: UserSpecialMembershipRequest) -> int | None:
    if not req.subscription:
        return None
    revoke_after_days = req.subscription.metadata.get("revokeAfterDays")
    if isinstance(revoke_after_days, int) and revoke_after_days > 0:
        return revoke_after_days
    return None


def _schedule_temporary_revocation(req: UserSpecialMembershipRequest) -> None:
    revoke_after_days = _get_revoke_after_days(req)
    if revoke_after_days is None:
        logger.warning(
            f"[instance:{req.pk}] STATUS_APPROVED_TEMPORARY but revokeAfterDays is missing/invalid, skipping scheduling"
        )
        return
    revoke_at = timezone.now() + timedelta(days=revoke_after_days)
    revoke_special_membership_request.apply_async(
        kwargs={"instance_id": req.pk}, eta=revoke_at
    )


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_special_membership_request_created(self, instance_id: int) -> None:
    """
    THe request has been created outside of the flow in the admin panel.
    In this case we should manually apply the post-create actions.

    Args:
        self: The task instance.
        instance_id (int): The ID of the UserSpecialMembershipRequest instance that was created.
    """
    # get request
    try:
        req = UserSpecialMembershipRequest.objects.get(pk=instance_id)
    except UserSpecialMembershipRequest.DoesNotExist:
        logger.error(f"[UserSpecialMembershipRequest:{instance_id}] DoesNotExist :(")
        return
    logger.info(
        f"[UserSpecialMembershipRequest:{instance_id}] triggered signals after_special_membership_request_created, for user={req.user.username} subscription={req.subscription.title if req.subscription else 'None'} status={req.status}"
    )

    if (
        req.status == UserSpecialMembershipRequest.STATUS_PENDING
        and _is_temporary_auto_accept_enabled(req)
    ):
        revoke_after_days = _get_revoke_after_days(req)
        if revoke_after_days is None:
            logger.warning(
                f"[instance:{instance_id}] enableTemporaryAutomaticAcceptance is true but revokeAfterDays is missing or invalid, continuing regular pending flow"
            )
        else:
            req.status = UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY
            req.save()
            logger.info(
                f"[instance:{instance_id}] auto-accepted as temporary for {revoke_after_days} day(s)"
            )
            # The save above triggers the update task via signal, which applies bitmap,
            # sends the temporary-approval email, and schedules revocation.
            return

    apply_special_membership_to_bitmap(instance=req, created=True, logger=logger)
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
    TODO:
    If its status is "STATUS_APPROVED", notify the user with the details of the special membership granted.
    If its status is "STATUS_PENDING", notify the institution reviewer with the details of the request AND to the user that their request is pending review.
    If its status is "STATUS_REJECTED", notify the user that their request has been rejected.

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
        instance=req, logger=logger
    )

    if req.status == UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY:
        _schedule_temporary_revocation(req)


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
    logger.info(
        f"[instance:{instance_id}] temporary membership revoked for user={req.user.pk}"
    )
    apply_special_membership_to_bitmap(instance=req, created=False, logger=logger)
    send_email_after_user_special_membership_request_updated(
        instance=req, logger=logger
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
        temporary_expires_at__lt=timezone.now()
    )
    
    count = expired_requests.count()
    if count == 0:
        logger.info("No expired temporary memberships found to revoke.")
        return

    logger.info(f"Found {count} expired temporary memberships to revoke.")
    
    for req in expired_requests:
        revoke_special_membership_request.delay(instance_id=req.pk)
