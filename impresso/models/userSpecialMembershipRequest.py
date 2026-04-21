from typing import Any, List, Optional, TypedDict
from django.db import models
from django.contrib.auth.models import User
from .specialMembershipDataset import SpecialMembershipDataset
from django.utils import timezone


# --- Typing Definition for Changelog Entry ---
class ChangelogEntry(TypedDict):
    """
    Defines the strict type structure for a special membership request changelog entry.
    """

    status: (
        str  # e.g., "pending", "approved", "approved_temporary", "rejected", "revoked"
    )
    subscription: Optional[str]  # The title of the subscription
    date: str  # ISO formatted date string
    reviewer: Optional[str]  # Username of the reviewer
    notes: str  # Additional notes (guaranteed to be a string, not None)


class UserSpecialMembershipRequest(models.Model):
    """
    UserRequest model represents a request made by a user for a subscription.
    Note: The unique_together constraint ensures that each user can only have one request per subscription,
        regardless of the reviewer. This is to prevent duplicate requests for the same subscription by the same user.
    Check post_save_user_special_membership_request signal to handle the approval process.

    Attributes:
        STATUS_PENDING (str): Status indicating the request is pending.
        STATUS_APPROVED (str): Status indicating the request is approved.
        STATUS_APPROVED_TEMPORARY (str): Status indicating the request is temporarily approved.
        STATUS_REJECTED (str): Status indicating the request is rejected.
        STATUS_REVOKED (str): Status indicating the request has been revoked after temporary approval.

        user (ForeignKey): Foreign key to the User model representing the user making the request.
        reviewer (ForeignKey): Foreign key to the User model representing the reviewer of the request.
        subscription (ForeignKey): Foreign key to the SpecialMembershipDataset model representing the subscription requested.
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
    STATUS_APPROVED_TEMPORARY = "temporary"
    STATUS_REJECTED = "rejected"
    STATUS_REVOKED = "revoked"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="request")
    reviewer = models.ForeignKey(
        User, on_delete=models.SET_NULL, related_name="review", null=True, blank=True
    )
    subscription = models.ForeignKey(
        SpecialMembershipDataset,
        on_delete=models.SET_NULL,
        null=True,
        help_text="The special membership dataset being requested",
    )
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)
    temporary_expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Expiration date used for temporary automatic approvals",
    )
    status = models.CharField(
        max_length=10,
        default=STATUS_PENDING,
        choices=(
            (STATUS_PENDING, "Pending"),
            (STATUS_APPROVED, "Approved"),
            (STATUS_APPROVED_TEMPORARY, "Approved (Temporary)"),
            (STATUS_REJECTED, "Rejected"),
            (STATUS_REVOKED, "Revoked"),
        ),
    )
    changelog = models.JSONField(null=True, blank=True, default=list)
    notes = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} Request for {self.subscription.title if self.subscription else '[deleted subscription]'}"

    class Meta:
        unique_together = ("user", "subscription")
        verbose_name = "User Special Membership Request"
        verbose_name_plural = "User Special Membership Requests"
        db_table = "impresso_userrequest"

    def save(self, *args: Any, **kwargs: Any) -> None:
        changelog_entry: ChangelogEntry = {
            "status": self.status,
            "subscription": self.subscription.title if self.subscription else None,
            "date": (
                timezone.now().isoformat()
                if not self.pk
                else self.date_last_modified.isoformat()
            ),
            "reviewer": self.reviewer.username if self.reviewer else None,
            "notes": self.notes if self.notes else "",
        }
        current_changelog: List[ChangelogEntry] = self.changelog or []
        current_changelog.append(changelog_entry)
        self.changelog = current_changelog  # Assign the updated list back
        super().save(*args, **kwargs)
