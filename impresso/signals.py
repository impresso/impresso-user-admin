import logging
import sys
from django.conf import settings
from django.contrib.auth.models import Group, User
from impresso.models.userBitmap import UserBitmap
from impresso.models.userChangePlanRequest import UserChangePlanRequest
from impresso.models.userSpecialMembershipRequest import UserSpecialMembershipRequest
from impresso.tasks.userChangePlanRequest_task import after_change_plan_request_updated
from impresso.tasks.userSpecialMembershipRequest_tasks import (
    after_special_membership_request_updated,
)

logger = logging.getLogger(__name__)


def create_default_groups(sender, **kwargs):
    """
    Creates default user groups based on the settings.

    This function is typically used as a signal handler to create default
    user groups when certain events occur (e.g., when a user is created).

    Args:
      sender (Any): The sender of the signal.
      **kwargs: Additional keyword arguments passed by the signal.

    Settings:
      IMPRESSO_DEFAULT_GROUP_USERS (list of tuple): A list of tuples where each
      tuple contains the slug and the name of the group to be created.

    Logs:
      Logs the creation of default groups using the logger.

    Example:
      default_groups = [
        ('admin', 'Administrators'),
        ('editor', 'Editors'),
        ('viewer', 'Viewers')
      ]
      settings.IMPRESSO_DEFAULT_GROUP_USERS = default_groups
      create_default_groups(sender=None)
    """
    default_groups = settings.IMPRESSO_DEFAULT_GROUP_USERS

    logger.info(f"Creating default groups: {[a[0] for a in default_groups]}")
    # each item is a tuple, containing the slud and the name of the group
    for group_slug, group_name in default_groups:
        g, created = Group.objects.get_or_create(name=group_slug)
        if created:
            logger.info(f"Group created successfully: {group_slug}")
        else:
            logger.info(f"Group already exists: {g.id} - {group_slug}")


def post_save_user_change_plan_request(sender, instance, created, **kwargs):
    logger.info(
        f"@post_save UserChangePlanRequest for user={instance.user.pk} plan={instance.plan.name} status=instance.status"
    )
    if instance.status == UserChangePlanRequest.STATUS_APPROVED:
        instance.user.groups.add(instance.plan)
    elif instance.status in [
        UserChangePlanRequest.STATUS_REJECTED,
        UserChangePlanRequest.STATUS_PENDING,
    ]:
        instance.user.groups.remove(instance.plan)
    after_change_plan_request_updated.delay(user_id=instance.user.pk)


def post_save_user_special_membership_request(
    sender, instance: UserSpecialMembershipRequest, created, **kwargs
):
    logger.info(
        f"@post_save UserSpecialMembershipRequest for user={instance.user.pk} subscription={instance.subscription.title if instance.subscription else 'None'} status={instance.status}"
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
    after_special_membership_request_updated.delay(instance_id=instance.pk)
