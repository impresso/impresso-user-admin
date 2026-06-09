from typing import Optional, TypedDict
from numbers import Real
from django.conf import settings
from django.db import models
from django.db.models import Max


# --- Typing Definition for Metadata---
class Metadata(TypedDict, total=False):
    """
    Defines the strict type structure for a special membership dataset metadata.
    """

    modality: Optional[str]  # e.g., "cc_reviewer", "notify_reviewer"
    enableTemporaryAutomaticApproval: Optional[bool]
    revokeAfterDays: Optional[float]
    revokeTemporaryAutomaticApprovalAfterDays: Optional[float]


class SpecialMembershipDataset(models.Model):
    """
    SpecialMembershipDataset model represents a special membership dataset
    that users can subscribe to for additional access rights.

    Attributes:
        title (CharField): The title of the special membership dataset.
        bitmap_position (PositiveIntegerField): The position in the user's bitmap representing this dataset.
        metadata (Metadata): Additional metadata related to the dataset.
        reviewer (ForeignKey): Foreign key to the User model representing the reviewer of the dataset.

    Methods:
        __str__(): Returns a string representation of the SpecialMembershipDataset instance.
        save(*args, **kwargs): Overrides the save method to automatically assign a bitmap position integer number if not set.

    Meta:
        verbose_name (str): Human-readable name for the model.
        verbose_name_plural (str): Human-readable plural name for the model.

    """

    title = models.CharField(max_length=255, db_column="name")
    bitmap_position = models.PositiveIntegerField(
        unique=True,
        null=True,
        blank=True,
    )
    metadata: Metadata = models.JSONField(default=dict, blank=True)

    reviewer = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        related_name="reviewed_datasets",
        null=True,
        blank=True,
    )

    METADATA_MODALITY = "modality"
    METADATA_ENABLE_TEMPORARY_AUTOMATIC_APPROVAL = "enableTemporaryAutomaticApproval"
    METADATA_REVOKE_AFTER_DAYS = "revokeAfterDays"
    METADATA_REVOKE_TEMPORARY_AUTOMATIC_APPROVAL_AFTER_DAYS = (
        "revokeTemporaryAutomaticApprovalAfterDays"
    )

    METADATA_ALLOWED_KEYS = {
        METADATA_MODALITY,
        METADATA_ENABLE_TEMPORARY_AUTOMATIC_APPROVAL,
        METADATA_REVOKE_AFTER_DAYS,
        METADATA_REVOKE_TEMPORARY_AUTOMATIC_APPROVAL_AFTER_DAYS,
    }

    def __str__(self):
        return self.title

    @property
    def modality(self) -> Optional[str]:
        return self.metadata.get("modality")

    @property
    def enable_temporary_automatic_acceptance(self) -> Optional[bool]:
        value = self.metadata.get(self.METADATA_ENABLE_TEMPORARY_AUTOMATIC_APPROVAL)
        return bool(value) if value is not None else None

    @property
    def revoke_after_days(self) -> Optional[float]:
        value = self.metadata.get(self.METADATA_REVOKE_AFTER_DAYS)
        return float(value) if isinstance(value, Real) else None

    @property
    def revoke_temporary_automatic_approval_after_days(self) -> Optional[float]:
        value = self.metadata.get(
            self.METADATA_REVOKE_TEMPORARY_AUTOMATIC_APPROVAL_AFTER_DAYS
        )
        return float(value) if isinstance(value, Real) else None

    def is_temporary_auto_accept_enabled(self) -> bool:
        return bool(self.enable_temporary_automatic_acceptance)

    def is_modality_cc_reviewer_enabled(self) -> bool:
        return (
            self.modality
            == settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
        )

    def resolve_temporary_automatic_approval_after_days(
        self, default_days: Optional[float]
    ) -> float:
        """
        Returns the number of days after which a temporary approval
        should be revoked.

        Priority:
        1. metadata["revokeTemporaryAutomaticApprovalAfterDays"]
        2. provided default_days
        3. Django settings fallback
        """
        revoke_temporary_automatic_approval_after_days = self.metadata.get(
            self.METADATA_REVOKE_TEMPORARY_AUTOMATIC_APPROVAL_AFTER_DAYS
        )
        if (
            isinstance(revoke_temporary_automatic_approval_after_days, Real)
            and float(revoke_temporary_automatic_approval_after_days) > 0.0
        ):
            return float(revoke_temporary_automatic_approval_after_days)
        if isinstance(default_days, Real) and default_days > 0:
            return float(default_days)
        return float(
            settings.IMPRESSO_SPECIAL_MEMBERSHIP_TEMPORARY_APPROVAL_DEFAULT_DAYS
        )

    def resolve_revoke_after_days(
        self, default_days: Optional[float]
    ) -> Optional[float]:
        """
        Returns the number of days after which a subscription should be revoked.

        Priority:
        1. metadata["revokeAfterDays"]
        2. provided default_days
        3. None (indicating no revocation)
        """
        revoke_after_days = self.metadata.get(self.METADATA_REVOKE_AFTER_DAYS)
        if isinstance(revoke_after_days, Real) and float(revoke_after_days) > 0.0:
            return float(revoke_after_days)
        if isinstance(default_days, Real) and default_days > 0:
            return float(default_days)
        return None

    class Meta:
        verbose_name = "Special Membership Access"
        verbose_name_plural = "Special Membership Accesses"
        db_table = "impresso_datasetbitmapposition"

    def save(self, *args, **kwargs):
        if self.bitmap_position is None:
            max_position = SpecialMembershipDataset.objects.aggregate(
                Max("bitmap_position")
            )["bitmap_position__max"]
            self.bitmap_position = 0 if max_position is None else max_position + 1
        super().save(*args, **kwargs)
