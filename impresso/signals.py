import logging
from django.conf import settings
from django.contrib.auth.models import Group, User
from impresso.tasks import after_change_plan_request_updated

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
    after_change_plan_request_updated.delay(user_id=instance.user.pk)
    #     # remove from the group if the user is attached to that group
    #     if self.plan in self.user.groups.all():
    #         self.user.groups.remove(self.plan)
    # if instance.status == instance.STATUS_APPROVED:
    #     after_plan_change_accepted.delay(user_id=instance.user.pk)
    # elif instance.status == instance.STATUS_REJECTED:
    #     # remove from the group if the user is attached to that group
    #     # instance.user.groups.remove(instance.plan)
    #     pass
