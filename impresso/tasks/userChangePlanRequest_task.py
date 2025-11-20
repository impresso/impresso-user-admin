from typing import Dict
from celery import shared_task
from celery.utils.log import get_task_logger
from django.db.utils import IntegrityError
from django.contrib.auth.models import Group

from impresso.utils.tasks.account import (
    send_email_plan_change_accepted,
    send_email_plan_change_rejected,
)

from ..models import UserChangePlanRequest
from ..celery import app

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def create_change_plan_request(self, user_id: int, plan: str) -> Dict:
    """
    Create a change plan request for the user.
    """
    try:
        plan_as_group = Group.objects.get(name=plan)
        # Django's .create() method handles looking up ForeignKey objects
        # when provided with object IDs (user_id and subscription_id).
        UserChangePlanRequest.objects.get_or_create(user_id=user_id, plan=plan_as_group)
        logger.info(
            f"Created UserChangePlanRequest for user_id={user_id} plan={plan_as_group.name}"
        )
        return {
            "status": "created",
            "message": "Request created successfully",
            "user_id": user_id,
            "plan": plan_as_group.name,
        }
    except IntegrityError:
        # This catches the unique_together constraint violation (user, subscription)
        # This is a common and important check to keep.
        logger.error(
            f"IntegrityError: Could not create UserChangePlanRequest for user_id={user_id} plan={plan_as_group.name} - request already exists. We just ignore."
        )
        return {
            "status": "skipped_duplicate",
            "message": "Request already exists",
            "user_id": user_id,
            "plan": plan_as_group.name,
        }


@app.task(
    bind=True,
    autoretry_for=(Exception,),
    exponential_backoff=2,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def after_change_plan_request_updated(self, user_id: int) -> None:
    """
    Accepts user request (if it is not rejected!) then
    sends an email notification for an accepted plan change request.

    Args:
        self: The task instance.
        user_id (int): The ID of the user requesting the plan change.

    Returns:
        None
    """
    # get request
    try:
        req = UserChangePlanRequest.objects.get(user_id=user_id)
    except UserChangePlanRequest.DoesNotExist:
        logger.error(f"[user:{user_id}] UserChangePlanRequest.DoesNotExist")
        return
    logger.info(f"[user:{user_id}] plan change to {req.plan.name} status {req.status}")

    if req.status == UserChangePlanRequest.STATUS_APPROVED:
        send_email_plan_change_accepted(
            user_id=user_id, plan=req.plan.name, logger=logger
        )
    elif req.status == UserChangePlanRequest.STATUS_REJECTED:
        send_email_plan_change_rejected(
            user_id=user_id, plan=req.plan.name, logger=logger
        )
