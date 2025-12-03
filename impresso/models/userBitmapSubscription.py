from django.db import models
from .userBitmap import UserBitmap
from .specialMembershipDataset import SpecialMembershipDataset


class UserBitmapSubscription(models.Model):
    userbitmap = models.ForeignKey(
        UserBitmap, on_delete=models.CASCADE, db_column="userbitmap_id"
    )
    specialmembershipdataset = models.ForeignKey(
        SpecialMembershipDataset,
        on_delete=models.CASCADE,
        db_column="datasetbitmapposition_id",  # Your old column name
    )

    class Meta:
        db_table = "impresso_userbitmap_subscriptions"  # Your existing table name
        unique_together = [["userbitmap", "specialmembershipdataset"]]
        verbose_name = "User Special Membership Access"
        verbose_name_plural = "User Special Membership Accesses"
