from typing import Dict
from celery.utils.log import get_task_logger
from django.db.utils import IntegrityError

from impresso.models.specialMembershipDataset import SpecialMembershipDataset
from celery import shared_task
from ..celery import app
from ..models.userSpecialMembershipRequest import UserSpecialMembershipRequest

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def create_special_membership_request(self, user_id: int, subscription_id: int) -> Dict:
    """
    Celery task to create a new UserSpecialMembershipRequest. This is required because
    the creation process involves custom save() logic and email handling after saving.
    """
    try:
        # Django's .create() method handles looking up ForeignKey objects
        # when provided with object IDs (user_id and subscription_id).
        UserSpecialMembershipRequest.objects.create(
            user_id=user_id, subscription_id=subscription_id
        )
        logger.info(
            f"Created UserSpecialMembershipRequest for user_id={user_id} subscription_id={subscription_id}"
        )
        return {
            "status": "created",
            "message": "Request created successfully",
            "user_id": user_id,
            "subscription_id": subscription_id,
        }
    except IntegrityError:
        # This catches the unique_together constraint violation (user, subscription)
        # This is a common and important check to keep.
        logger.error(
            f"IntegrityError: Could not create UserSpecialMembershipRequest for user_id={user_id} subscription_id={subscription_id} - request already exists. Skipping."
        )
        return {
            "status": "skipped_duplicate",
            "message": "Request already exists",
            "user_id": user_id,
            "subscription_id": subscription_id,
        }


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
    # here we can add additional actions, e.g., notify the institution via email if there's a reviewer assigned
    # TODO: implement email notification to institution reviewer if needed
