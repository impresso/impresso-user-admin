from django.contrib.auth.models import User
from django.conf import settings
from typing import Tuple, Optional


def get_plan_from_user_groups(user: User) -> Tuple[str, Optional[str]]:
  """
  Get the plan from the user's groups.

  This function determines the user's plan based on the groups they belong to.
  It checks the user's groups and returns the corresponding plan label and group name.

  Args:
    user (User): The user object.

  Returns:
    Tuple[str, Optional[str]]: A tuple containing the plan label and the plan group name.
                   If the user does not belong to any group, the group name is None.
  """
  if not user.groups.exists():
    return (settings.IMPRESSO_GROUP_USER_PLAN_NONE_LABEL, None)

  # Retrieve the names of the user's groups
  user_groups_names = [n for n in user.groups.values_list("name", flat=True)]

  # Default to the basic plan
  plan_group = settings.IMPRESSO_GROUP_USER_PLAN_BASIC
  plan_label = settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL

  # Check for specific plans based on group membership
  if settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER in user_groups_names:
    plan_group = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER
    plan_label = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL
  elif settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL in user_groups_names:
    plan_group = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL
    plan_label = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL

  return (plan_label, plan_group)