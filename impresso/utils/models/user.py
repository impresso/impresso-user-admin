from django.contrib.auth.models import User
from django.conf import settings
from typing import Tuple, Optional


def get_plan_from_group_name(group_name: str) -> Tuple[str, Optional[str]]:
    """
    Get the plan from the group name.

    This function determines the plan based on the group name provided.
    It returns the corresponding plan label and group name.

    Args:
      group_name (str): The name of the group.

    Returns:
      Tuple[str, Optional[str]]: A tuple containing the plan label and the plan group name.
                     If the group name is not recognized, the group name is None.
    """
    if not group_name:
        return (settings.IMPRESSO_GROUP_USER_PLAN_NONE_LABEL, None)

    # Default to the basic plan
    plan_group = settings.IMPRESSO_GROUP_USER_PLAN_BASIC
    plan_label = settings.IMPRESSO_GROUP_USER_PLAN_BASIC_LABEL

    # Check for specific plans based on group membership
    if group_name == settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER:
        plan_group = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER_LABEL
    elif group_name == settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL:
        plan_group = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL
        plan_label = settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL_LABEL

    return (plan_label, plan_group)


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
