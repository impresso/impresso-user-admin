from __future__ import absolute_import

import time
from celery.utils.log import get_task_logger
from django.contrib.auth.models import User, Group
from ..celery import app
from ..models import Job
from ..models import UserChangePlanRequest
from ..utils.tasks import (
    TASKSTATE_INIT,
    update_job_progress,
    update_job_completed,
    is_task_stopped,
)

from ..utils.tasks.account import (
    send_emails_after_user_registration,
    send_emails_after_user_activation_plan_rejected,
    send_emails_after_user_activation,
    send_email_password_reset,
    send_email_plan_change,
    send_email_plan_change_rejected,
)
from ..utils.tasks.userBitmap import helper_update_user_bitmap

from .userSpecialMembershipRequest_tasks import *
from .userChangePlanRequest_task import *

logger = get_task_logger(__name__)


# Define a reusable decorator with default config
def default_task_config(func):
    return app.task(
        bind=True,
        autoretry_for=(Exception,),
        exponential_backoff=2,
        retry_kwargs={"max_retries": 5},
        retry_jitter=True,
    )(func)


def get_collection_as_obj(collection):
    return {
        "id": collection.pk,
        "name": collection.name,
        "description": collection.description,
        "status": collection.status,
        "date_created": collection.date_created.isoformat(),
    }


@default_task_config
def echo(self, message):
    logger.info(f"Echo: {message}")
    response = f"Hello world. This is your message: {message}"
    return response


@default_task_config
def test_progress(self, job_id, sleep=100, pace=0.01, progress=0.0):
    # get the job so that we can update its status
    job = Job.objects.get(pk=job_id)

    extra = {
        "pace": pace,
        "sleep": sleep,
    }

    if is_task_stopped(
        task=self, job=job, progress=progress, extra=extra, logger=logger
    ):
        return

    update_job_progress(
        task=self, job=job, progress=progress, extra=extra, logger=logger
    )

    if progress < 1.0:
        # do heavy stuff during this time
        time.sleep(sleep)
        # call the same function right after
        test_progress.delay(
            job_id=job.pk, sleep=sleep, pace=pace, progress=progress + pace
        )
        return
    update_job_completed(task=self, job=job, extra=extra, logger=logger)


@default_task_config
def test(self, user_id: int, sleep: int = 1, pace: float = 0.05):
    """
    Initiates a test job and starts the test_progress task.

    Args:
        self: The instance of the class.
        user_id (int): The ID of the user initiating the test.
        sleep (int, optional): The sleep duration between progress updates. Defaults to 1.
        pace (float, optional): The pace of progress updates. Defaults to 0.05.

    Returns:
        None
    """
    # save current job then start test_progress task.
    job = Job.objects.create(type=Job.TEST, status=Job.RUN, creator_id=user_id)
    logger.info(f"[job:{job.pk} user:{user_id}] launched!")
    # stat loop
    update_job_progress(task=self, job=job, taskstate=TASKSTATE_INIT, progress=0.0)
    test_progress.delay(job_id=job.pk, sleep=sleep, pace=pace)


@default_task_config
def after_user_registered(self, user_id):
    logger.info(f"[user:{user_id}] just registered")
    # send confirmation email to the registered user
    # and send email to impresso admins
    send_emails_after_user_registration(user_id=user_id, logger=logger)


@default_task_config
def after_user_activation(self, user_id):
    logger.info(f"[user:{user_id}] is now active")
    # send confirmation email to the registered user
    # and send email to impresso admins
    send_emails_after_user_activation(user_id=user_id, logger=logger)


@default_task_config
def after_user_activation_plan_rejected(self, user_id: int) -> None:
    """
    Sends an email notification after a user is activated but only on the basic plan,
    thus rejecting initial plan requested.

    Args:
        self: The task instance.
        user_id (int): The ID of the user who was activated.

    Returns:
        None
    """
    logger.info(f"[user:{user_id}] is now active, but on BASIC PLAN")

    send_emails_after_user_activation_plan_rejected(user_id=user_id, logger=logger)


@default_task_config
def email_password_reset(
    self,
    user_id: int,
    token: str = "nonce",
    callback_url: str = "https://impresso-project.ch/app/reset-password",
) -> None:
    """
    Send a password reset email to the user containing a reset link.

    Args:
        self: Celery task instance (automatically provided by Celery).
        user_id (int): The unique identifier of the user requesting password reset.
        token (str, optional): The password reset token/nonce to include in the reset link.
            Defaults to "nonce".
        callback_url (str, optional): The base URL for the password reset callback.
            Defaults to "https://impresso-project.ch/app/reset-password".

    Returns:
        None

    Raises:
        Handled internally by the underlying `send_email_password_reset` function.

    Example:
        >>> email_password_reset.delay(user_id="12345", token="abc123xyz")

    Note:
        This task is decorated with @default_task_config which applies default
        Celery configuration settings (retry policy, routing, etc.).
    """
    logger.info(f"[user:{user_id}] requested password reset!")
    send_email_password_reset(
        user_id=user_id, token=token, callback_url=callback_url, logger=logger
    )


@default_task_config
def email_plan_change(self, user_id: int, plan: str) -> None:
    """
    Sends an email notification for a user's plan change request.

    Args:
        self: The task instance.
        user_id (int): The ID of the user requesting the plan change.
        plan (str, optional): The new plan requested by the user. Defaults to None.

    Returns:
        None
    """
    logger.info(f"[user:{user_id}] requested plan change to {plan}!")
    send_email_plan_change(user_id=user_id, plan=plan, logger=logger)


@default_task_config
def add_user_to_group_task(self, user_id: int, group_name: str) -> None:
    """
    Task to add a user to a group.

    Args:
        user_id (int): The ID of the user to be added to the group.
        group_name (str): The name of the group to which the user will be added.

    Returns:
        int: The ID of the user after being added to the group.
    """
    logger.info(f"[user:{user_id}] adding user to group {group_name}")
    user = User.objects.get(id=user_id)
    group = Group.objects.get(name=group_name)
    user.groups.add(group)


@default_task_config
def remove_user_from_group_task(self, user_id: int, group_name: str) -> None:
    """
    Task to remove a user from a group.

    Args:
        user_id (int): The ID of the user to be removed from the group.
        group_name (str): The name of the group from which the user will be removed.

    Returns:
        int: The ID of the user after being removed from the group.
    """
    logger.info(f"[user:{user_id}] removing user from group {group_name}")
    user = User.objects.get(id=user_id)
    group = Group.objects.get(name=group_name)
    user.groups.remove(group)


@default_task_config
def after_plan_change_rejected(self, user_id: int) -> None:
    """
    Rejects user request (if it is not already accepted!) then
    sends an email notification for a rejected plan change request.

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
        logger.error(f"UserChangePlanRequest.DoesNotExist for user {user_id}")
        return
    # if request is not PENDING, send out an error email.
    if req.status == UserChangePlanRequest.STATUS_APPROVED:
        logger.error(
            f"[user:{user_id}] plan change to {req.plan.name} is APPROVED, can't reject. Change the status in the DB before !"
        )
    logger.info(
        f"[user:{user_id}] request to change plan to {req.plan.name} has been REJECTED!"
    )
    # save Rejected status to the plan request
    req.status = UserChangePlanRequest.STATUS_REJECTED
    req.save()
    # send confirmation email to the registered user
    send_email_plan_change_rejected(user_id=user_id, plan=req.plan.name, logger=logger)


@default_task_config
def update_user_bitmap_task(self, user_id):
    """
    Update the user bitmap for the given user.
    """
    logger.info(f"User bitmap update request for user {user_id}")
    # save current job!
    job = Job.objects.create(
        type=Job.UPDATE_USER_BITMAP, creator_id=user_id, status=Job.RUN
    )
    serialized_userBitmap = helper_update_user_bitmap(user_id=user_id)
    # done!
    update_job_completed(
        task=self,
        job=job,
        message="User bitmap updated!",
        extra={"userBitmap": serialized_userBitmap},
    )
    return serialized_userBitmap
