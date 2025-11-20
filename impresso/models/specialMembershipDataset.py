from django.db import models
from django.db.models import Max


class SpecialMembershipDataset(models.Model):
    """
    SpecialMembershipDataset model represents a special membership dataset
    that users can subscribe to for additional access rights.

    Attributes:
        title (CharField): The title of the special membership dataset.
        bitmap_position (PositiveIntegerField): The position in the user's bitmap representing this dataset.
        metadata (JSONField): Additional metadata related to the dataset.
        reviewer (ForeignKey): Foreign key to the User model representing the reviewer of the dataset.

    Methods:
        __str__(): Returns a string representation of the SpecialMembershipDataset instance.
        save(*args, **kwargs): Overrides the save method to automatically assign a bitmap position integer number if not set.

    Meta:
        verbose_name (str): Human-readable name for the model.
        verbose_name_plural (str): Human-readable plural name for the model.

    """

    title = models.CharField(max_length=255)
    bitmap_position = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    reviewer = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        related_name="reviewed_datasets",
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Special Membership Access"
        verbose_name_plural = "Special Membership Accesses"

    def save(self, *args, **kwargs):
        if self.bitmap_position is None:
            max_position = SpecialMembershipDataset.objects.aggregate(
                Max("bitmap_position")
            )["bitmap_position__max"]
            self.bitmap_position = 0 if max_position is None else max_position + 1
        super().save(*args, **kwargs)
