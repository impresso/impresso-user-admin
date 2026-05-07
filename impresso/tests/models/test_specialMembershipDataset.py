from django.conf import settings
from django.test import TestCase

from impresso.models import SpecialMembershipDataset


class SpecialMembershipDatasetMetadataMethodsTestCase(TestCase):
    def test_is_temporary_auto_accept_enabled(self) -> None:
        dataset_enabled = SpecialMembershipDataset.objects.create(
            title="Dataset Enabled",
            metadata={"enableTemporaryAutomaticAcceptance": True},
        )
        dataset_disabled = SpecialMembershipDataset.objects.create(
            title="Dataset Disabled",
            metadata={"enableTemporaryAutomaticAcceptance": False},
        )

        self.assertTrue(dataset_enabled.is_temporary_auto_accept_enabled())
        self.assertFalse(dataset_disabled.is_temporary_auto_accept_enabled())

    def test_is_modality_cc_reviewer_enabled(self) -> None:
        dataset_cc = SpecialMembershipDataset.objects.create(
            title="Dataset CC",
            metadata={
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER
            },
        )
        dataset_notify = SpecialMembershipDataset.objects.create(
            title="Dataset Notify",
            metadata={
                "modality": settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER
            },
        )

        self.assertTrue(dataset_cc.is_modality_cc_reviewer_enabled())
        self.assertFalse(dataset_notify.is_modality_cc_reviewer_enabled())

    def test_resolve_revoke_after_days_from_metadata(self) -> None:
        dataset = SpecialMembershipDataset.objects.create(
            title="Dataset Revoke",
            metadata={"revokeAfterDays": 2.5},
        )

        self.assertEqual(dataset.resolve_revoke_after_days(default_days=7), 2.5)

    def test_resolve_revoke_after_days_falls_back_to_default(self) -> None:
        dataset_missing = SpecialMembershipDataset.objects.create(
            title="Dataset Missing",
            metadata={},
        )
        dataset_zero = SpecialMembershipDataset.objects.create(
            title="Dataset Zero",
            metadata={"revokeAfterDays": 0},
        )
        dataset_invalid = SpecialMembershipDataset.objects.create(
            title="Dataset Invalid",
            metadata={"revokeAfterDays": "seven"},
        )

        self.assertEqual(dataset_missing.resolve_revoke_after_days(default_days=7), 7.0)
        self.assertEqual(dataset_zero.resolve_revoke_after_days(default_days=7), 7.0)
        self.assertEqual(dataset_invalid.resolve_revoke_after_days(default_days=7), 7.0)
        self.assertEqual(
            dataset_zero.resolve_revoke_after_days(default_days=-7),
            settings.IMPRESSO_SPECIAL_MEMBERSHIP_TEMPORARY_APPROVAL_DEFAULT_DAYS,
        )
