from django.db import models
from django.contrib.auth.models import User


class UserBitmap(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="bitmap")
    bitmap = models.BinaryField()

    def __str__(self):
        return f"{self.user.username} Bitmap"

    class Meta:
        verbose_name = "User Bitmap"
        verbose_name_plural = "User Bitmaps"
