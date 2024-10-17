import json
from django.core.serializers import serialize
from ...models import UserBitmap


def update_user_bitmap(user_id):
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
    bitmap = user_bitmap.get_up_to_date_bitmap()
    bitmap_bytes = bitmap.to_bytes((bitmap.bit_length() + 7) // 8, byteorder="big")
    user_bitmap.bitmap = bitmap_bytes
    user_bitmap.save()
    serialized = json.loads(serialize("json", [user_bitmap]))[0].get("fields")
    return {
        "date_accepted_terms": serialized.get("date_accepted_terms"),
        "bitmap_base64": serialized.get("bitmap"),
        "subscriptions": serialized.get("subscriptions"),
        "bitmap": bin(user_bitmap.get_bitmap_as_int()),
        "plan": user_bitmap.get_user_plan(),
    }
