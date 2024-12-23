from django.db import models
from django.contrib.auth.models import User, Group


class UserChangePlanRequest(models.Model):
    """
    UserChangePlanRequest model
    This model represents a request made by a user to change their subscription plan.
    As soon as this model is saved and the status is STATUS_APPROVED or STATUS_REJECTED,
    the user groups are updated by the celery task `after_change_plan_request_updated`

    Note:
        Each user can have only one change plan request item. This ensures that all changes are tracked within a single item in the database.

    Attributes:
        STATUS_PENDING (str): Constant for pending status.
        STATUS_APPROVED (str): Constant for approved status.
        STATUS_REJECTED (str): Constant for rejected status.
        user (OneToOneField): A one-to-one relationship with the User model.
        plan (ForeignKey): A foreign key relationship with the Group model, representing the subscription plan.
        date_created (DateTimeField): The date and time when the request was created.
        date_last_modified (DateTimeField): The date and time when the request was last modified.
        status (CharField): The current status of the request, with choices for pending, approved, and rejected.
        changelog (JSONField): A JSON field to store the history of changes made to the request.
        notes (TextField): Additional notes related to the request.

    Methods:
        __str__(): Returns a string representation of the request.
        save(*args, **kwargs): Overrides the save method to handle changelog updates and status changes.

    Meta:
        verbose_name (str): Human-readable name for the model.
        verbose_name_plural (str): Human-readable plural name for the model.
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="changePlanRequest",
    )
    plan = models.ForeignKey(Group, on_delete=models.SET_NULL, null=True)
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
        return f"{self.user.username} Request for {self.plan.name if self.plan else '[deleted subscription]'}"

    class Meta:
        verbose_name = "User Change Plan Request"
        verbose_name_plural = "User Change Plan Requests"

    def save(self, *args, **kwargs):
        if self.pk:
            # Prepare the new changelog entry
            changelog_entry = {
                "status": self.status,
                "plan": self.plan.name if self.plan else None,
                "date": self.date_last_modified.isoformat(),
                "notes": self.notes if self.notes else "",
            }

            # Append the new entry to the changelog list
            self.changelog.append(changelog_entry)
        super().save(*args, **kwargs)
