from django.db import models
from django.db.models import Max


class DatasetBitmapPosition(models.Model):
    name = models.CharField(max_length=255)
    bitmap_position = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.bitmap_position is None:
            max_position = DatasetBitmapPosition.objects.aggregate(
                Max("bitmap_position")
            )["bitmap_position__max"]
            self.bitmap_position = 0 if max_position is None else max_position + 1
        super().save(*args, **kwargs)
