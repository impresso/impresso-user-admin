from ...models import UserBitmap


def update_user_bitmap(user_id):
    user_bitmap = UserBitmap.objects.get(user_id=user_id)
    bitmap = user_bitmap.get_up_to_date_bitmap()
    bitmap_bytes = bitmap.to_bytes((user_bitmap.bit_length() + 7) // 8, byteorder="big")
    user_bitmap.bitmap = bitmap_bytes
    user_bitmap.save()
