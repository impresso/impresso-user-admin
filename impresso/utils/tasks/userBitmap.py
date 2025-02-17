import json
from django.core.serializers import serialize
from ...models import UserBitmap


def helper_update_user_bitmap(user_id: int) -> dict:
    """
    Updates the bitmap for a given user.

    This function updates user bitmap to the most recent version taken into account user
    groups, plan and terms of use acceptance.

    Args:
        user_id (int): The ID of the user whose bitmap needs to be updated.

    Returns:
        dict: A dictionary containing the updated bitmap as an integer.
    """
    user_bitmap = UserBitmap.objects.get(user_id=user_id)
    # update user bitmap
    user_bitmap.save()
    serialized = json.loads(serialize("json", [user_bitmap]))[0].get("fields")
    return serialized
