import logging
from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from .datasetBitmapPosition import DatasetBitmapPosition
from django.db.models.signals import m2m_changed
from ..utils.bitmask import int_to_bytes

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
    USER_PLAN_GUEST = 0b1
    USER_PLAN_AUTH_USER = 0b11
    USER_PLAN_EDUCATIONAL = 0b111
    USER_PLAN_RESEARCHER = 0b1011

    BITMAP_PLAN_MAX_LENGTH = 5

    def get_up_to_date_bitmap(self) -> bytes:
        """
        Get the bitmap using the groups the user is affiliated to and the affiliations
        to the DatasetBitmapPosition.
        All users are 0b1 by default, and the bitmap is updated to 0b11 if the user has accepted the terms of use.
        The bitmap is updated to 0b111 if the user is affiliated to the educational group, or to
        0b1101 if the user is affiliated to the researcher group.
        The remaining bits are defined by the user's affiliations to the DatasetBitmapPosition.

        Args:
            None

        Returns:
            bytes: The user's bitmap as a byte array.
        """
        # if the user hasn't accepted terms of use, return the default bitmap
        if not self.date_accepted_terms:
            return int_to_bytes(UserBitmap.USER_PLAN_GUEST)

        # get all groups the user is affiliated to as flat array, ordered by a-z
        groups = [group.name for group in self.user.groups.all()]
        if settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER in groups:
            value = UserBitmap.USER_PLAN_RESEARCHER
        elif settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL in groups:
            value = UserBitmap.USER_PLAN_EDUCATIONAL
        else:
            value = UserBitmap.USER_PLAN_AUTH_USER
        # print current bitmap
        # print(f"current bitmap: {bitmap:05b}")
        # get all user subscriptions
        subscriptions = list(self.subscriptions.values("name", "bitmap_position"))
        if not subscriptions:
            return int_to_bytes(value)
        # Set the bits for each subscription
        for s in subscriptions:
            value |= 1 << (s["bitmap_position"] + UserBitmap.BITMAP_PLAN_MAX_LENGTH)

        return int_to_bytes(value)

    def get_bitmap_as_int(self):
        return int.from_bytes(self.bitmap, byteorder="big")

    def get_bitmap_as_key_str(self):
        """
        Converts the bitmap to an integer and returns its binary representation as a string.

        Returns:
            str: The binary representation of the bitmap as a string, with the first two characters truncated.
        """
        return bin(self.get_bitmap_as_int())[2:]

    def get_user_plan(self):
        if not self.bitmap:
            return "- (no bitmap)"
        if not self.date_accepted_terms:
            return "- (terms not accepted)"
        # get the first bits of the bitmap up to the max length
        bitmap_int = self.get_bitmap_as_int()
        plan = bitmap_int & 0b1111
        if plan == UserBitmap.USER_PLAN_GUEST:
            return "guest"
        if plan == UserBitmap.USER_PLAN_AUTH_USER:
            return "basic"
        if plan == UserBitmap.USER_PLAN_EDUCATIONAL:
            return settings.IMPRESSO_GROUP_USER_PLAN_EDUCATIONAL
        if plan == UserBitmap.USER_PLAN_RESEARCHER:
            return settings.IMPRESSO_GROUP_USER_PLAN_RESEARCHER
        return bin(plan)

        # bitmap_plan = (
        #     bitmap_int >> (bitmap_length - UserBitmap.BITMAP_PLAN_MAX_LENGTH)
        # ) & 0b11111
        # if bitmap_plan == UserBitmap.USER_PLAN_GUEST:
        #     return "GUEST"
        # if bitmap_plan == UserBitmap.USER_PLAN_AUTH_USER:
        #     return "AUTH_USER"
        # if bitmap_plan == UserBitmap.USER_PLAN_EDUCATIONAL:
        #     return "EDUCATIONAL"
        # if bitmap_plan == UserBitmap.USER_PLAN_RESEARCHER:
        #     return "RESEARCHER"
        # return "AUTH_USER"

    def __str__(self):
        bitmap = self.get_bitmap_as_int()
        return f"{self.user.username} Bitmap {bin(bitmap)}"

    class Meta:
        verbose_name = "User Bitmap"
        verbose_name_plural = "User Bitmaps"

    def save(self, *args, **kwargs):
        if not self.date_accepted_terms:
            self.bitmap = int_to_bytes(UserBitmap.USER_PLAN_GUEST)
        else:
            self.bitmap = self.get_up_to_date_bitmap()
        super().save(*args, **kwargs)


def update_user_bitmap_on_subscriptions_changed(sender, instance, action, **kwargs):
    if action == "post_add" or action == "post_remove" or action == "post_clear":
        logger.info(f"User {instance.user} subscription changed, updating")
        instance.save()


def update_user_bitmap_on_user_groups_changed(
    sender, instance: User, action, **kwargs
) -> None:
    if action == "post_add" or action == "post_remove" or action == "post_clear":
        user_bitmap, created = UserBitmap.objects.get_or_create(user=instance)
        logger.info(
            f"User {instance} groups changed. {'Creating new bitmap.' if created else 'Updating bitmap.'}"
        )
        user_bitmap.save()


m2m_changed.connect(
    update_user_bitmap_on_subscriptions_changed,
    sender=UserBitmap.subscriptions.through,
)

m2m_changed.connect(
    update_user_bitmap_on_user_groups_changed,
    sender=User.groups.through,
)
