from django.db import models
from django.contrib.auth.models import User
from .datasetBitmapPosition import DatasetBitmapPosition


class UserRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="request")
    reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="review", null=True, blank=True
    )
    subscription = models.ForeignKey(
        DatasetBitmapPosition, on_delete=models.SET_NULL, null=True
    )
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=10,
        default=STATUS_PENDING,
        choices=(
            (STATUS_PENDING, "Pending"),
            (STATUS_APPROVED, "Approved"),
            (STATUS_REJECTED, "Rejected"),
        ),
    )
    changelog = models.JSONField(null=True, blank=True, default=list)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} Request for {self.subscription.name if self.subscription else '[deleted subscription]'}"

    class Meta:
        unique_together = ("user", "subscription")
        verbose_name = "User Subscription Request"
        verbose_name_plural = "User Subscription Requests"

    def save(self, *args, **kwargs):
        if self.pk:
            # Prepare the new changelog entry
            changelog_entry = {
                "status": self.status,
                "subscription": self.subscription.name if self.subscription else None,
                "date": self.date_last_modified.isoformat(),
                "reviewer": self.reviewer.username if self.reviewer else None,
                "notes": self.notes if self.notes else "",
            }

            # Append the new entry to the changelog list
            self.changelog.append(changelog_entry)

        super().save(*args, **kwargs)
