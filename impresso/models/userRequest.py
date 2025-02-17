from django.db import models
from django.contrib.auth.models import User
from .datasetBitmapPosition import DatasetBitmapPosition


class UserRequest(models.Model):
    """
    UserRequest model represents a request made by a user for a subscription.
    Note: The unique_together constraint ensures that each user can only have one request per subscription, 
        regardless of the reviewer. This is to prevent duplicate requests for the same subscription by the same user.
    
    Attributes:
        STATUS_PENDING (str): Status indicating the request is pending.
        STATUS_APPROVED (str): Status indicating the request is approved.
        STATUS_REJECTED (str): Status indicating the request is rejected.

        user (ForeignKey): Foreign key to the User model representing the user making the request.
        reviewer (ForeignKey): Foreign key to the User model representing the reviewer of the request.
        subscription (ForeignKey): Foreign key to the DatasetBitmapPosition model representing the subscription requested.
        date_created (DateTimeField): The date and time when the request was created.
        date_last_modified (DateTimeField): The date and time when the request was last modified.
        status (CharField): The current status of the request.
        changelog (JSONField): A list of changes made to the request.
        notes (TextField): Additional notes related to the request.
    
   
    Methods:
        __str__(): Returns a string representation of the UserRequest instance.
        save(*args, **kwargs): Overrides the save method to append changes to the changelog before saving.
    
    Meta:
        unique_together (tuple): Ensures that each user can only have one request per subscription.
        verbose_name (str): Human-readable name for the model.
        verbose_name_plural (str): Human-readable plural name for the model.
    """
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
