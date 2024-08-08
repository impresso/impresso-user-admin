from django.db import models
from django.contrib.auth.models import User
from .datasetBitmapPosition import DatasetBitmapPosition
from django.db.models.signals import m2m_changed


class UserBitmap(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="bitmap")
    bitmap = models.BinaryField(editable=False, null=True, blank=True)
    subscriptions = models.ManyToManyField(DatasetBitmapPosition)
    # Guest - Unregisted User	public	NA (True by default) used only for test purposes
    # Impresso Registered User 	impresso	Account created, no academic afiliation
    # Student or Teacher - Educational User	educational	Account created, educational academic afiliation
    # Researcher - Academic User	researcher	Account created, research academic afiliation
    USER_PLAN_GUEST = 0b10000
    USER_PLAN_AUTH_USER = 0b11000
    USER_PLAN_EDUCATIONAL = 0b11100
    USER_PLAN_RESEARCHER = 0b11110

    BITMAP_PLAN_MAX_LENGTH = 5

    def get_up_to_date_bitmap(self):
        """
        Get the bitmap using the groups the user is affiliated to and the affiliations to the DatasetBitmapPosition
        The four first bits (starting on the left, indices 0-3) are the ones relating to the user plans
        Then there is an empy bit (index 4) and the rest of the bits are for the user's subscriptions to the datasets.
        The user bitmap relating to user plans is cumulative, hence, any user that is a researcher (bit #3 = 1) has all preceeding
        bits also set to 1 : 1111 [archive bits...].
        All users have at least the "guest" bit set to 1 (bit #1): 10000 [archive bits, all 0]
        """
        # get all groups the user is affiliated to as flat array, ordered by a-z
        groups = [group.name for group in self.user.groups.all()]
        if "plan-researcher" in groups:
            bitmap = UserBitmap.USER_PLAN_RESEARCHER
        elif "plan-educational" in groups:
            bitmap = UserBitmap.USER_PLAN_EDUCATIONAL
        else:
            bitmap = UserBitmap.USER_PLAN_AUTH_USER
        # get all user subscriptions
        subscriptions = list(self.subscriptions.values("name", "bitmap_position"))
        # max bitmap position
        max_position = (
            max([x["bitmap_position"] for x in subscriptions])
            + UserBitmap.BITMAP_PLAN_MAX_LENGTH
        )
        # Shift the initial signature to the left by the max bit position
        bitmap = bitmap << max_position - UserBitmap.BITMAP_PLAN_MAX_LENGTH
        for subscription in subscriptions:
            # Use the bitmap position to set the corresponding bit
            position = (
                subscription["bitmap_position"] + UserBitmap.BITMAP_PLAN_MAX_LENGTH
            )
            bitmap |= 1 << (max_position - position)

        return bitmap

    def __str__(self):
        return f"{self.user.username} Bitmap"

    class Meta:
        verbose_name = "User Bitmap"
        verbose_name_plural = "User Bitmaps"


def update_user_bitmap(sender, instance, action, **kwargs):
    if action == "post_add":
        user_bitmap = instance.get_up_to_date_bitmap()
        bitmap_bytes = user_bitmap.to_bytes(
            (user_bitmap.bit_length() + 7) // 8, byteorder="big"
        )
        instance.bitmap = bitmap_bytes
        instance.save()


m2m_changed.connect(
    update_user_bitmap,
    sender=UserBitmap.subscriptions.through,
)
