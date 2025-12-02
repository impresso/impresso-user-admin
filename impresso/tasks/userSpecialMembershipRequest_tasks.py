from typing import Dict
from celery.utils.log import get_task_logger
from django.db.utils import IntegrityError

from impresso.models.specialMembershipDataset import SpecialMembershipDataset
from celery import shared_task
from ..celery import app
from ..models.userSpecialMembershipRequest import UserSpecialMembershipRequest
from impresso.utils.tasks.userSpecialMembershipRequest import (
    apply_special_membership_to_bitmap,
    send_email_after_user_special_membership_request_created,
    send_email_after_user_special_membership_request_updated,
)

logger = get_task_logger(__name__)


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
