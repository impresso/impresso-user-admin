import logging
from django.db import models
from django.contrib.auth.models import User
from .datasetBitmapPosition import DatasetBitmapPosition
from django.db.models.signals import m2m_changed

logger = logging.getLogger(__name__)


class UserBitmap(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="bitmap")
    bitmap = models.BinaryField(editable=False, null=True, blank=True)
    subscriptions = models.ManyToManyField(DatasetBitmapPosition, blank=True)
    # date of acceptance of the term of use
    date_accepted_terms = models.DateTimeField(null=True, blank=True)
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
        # if the user hasn't accepted terms of use, return the default bitmap
        if not self.date_accepted_terms:
            return UserBitmap.USER_PLAN_AUTH_USER
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
        # print current bitmap
        # print(f"current bitmap: {bitmap:05b}")
        # get all user subscriptions
        subscriptions = list(self.subscriptions.values("name", "bitmap_position"))
        if not subscriptions:
            return bitmap
        # max bitmap position
        max_position = (
            max([x["bitmap_position"] for x in subscriptions])
            + UserBitmap.BITMAP_PLAN_MAX_LENGTH
            + 1
        )
        # Shift the initial signature to the left by the max bit position
        bitmap = bitmap << max_position - UserBitmap.BITMAP_PLAN_MAX_LENGTH
        # print(f"current empty bitmap: {bitmap:05b}")
        for subscription in subscriptions:
            # Use the bitmap position to set the corresponding bit
            position = (
                subscription["bitmap_position"] + UserBitmap.BITMAP_PLAN_MAX_LENGTH
            )
            bitmap |= 1 << (max_position - position - 1)

        return bitmap

    def __str__(self):
        return f"{self.user.username} Bitmap"

    class Meta:
        verbose_name = "User Bitmap"
        verbose_name_plural = "User Bitmaps"


def update_user_bitmap(sender, instance, action, **kwargs):
    if action == "post_add" or action == "post_remove":
        logger.info(f"User {instance.user} subscription changed, updating")
        user_bitmap = instance.get_up_to_date_bitmap()
        bitmap_bytes = user_bitmap.to_bytes(
            (user_bitmap.bit_length() + 7) // 8, byteorder="big"
        )
        instance.bitmap = bitmap_bytes
        instance.save()
        logger.info(
            f"User {instance.user} subscription changed, bitmap updated to {user_bitmap:05b}"
        )


def update_user_bitmap_on_user_groups_changed(sender, instance, action, **kwargs):
    if action == "post_add" or action == "post_remove":
        user_bitmap, created = UserBitmap.objects.get_or_create(user=instance)
        logger.info(
            f"User {instance} groups changed. {'Creating new bitmap.' if created else 'Updating bitmap.'}"
        )
        bitmap = user_bitmap.get_up_to_date_bitmap()
        bitmap_bytes = bitmap.to_bytes((bitmap.bit_length() + 7) // 8, byteorder="big")
        user_bitmap.bitmap = bitmap_bytes
        user_bitmap.save()
        logger.info(f"User {instance} groups changed, bitmap updated to {bitmap:05b}")


m2m_changed.connect(
    update_user_bitmap,
    sender=UserBitmap.subscriptions.through,
)

m2m_changed.connect(
    update_user_bitmap_on_user_groups_changed,
    sender=User.groups.through,
)
