from datetime import timedelta
from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from django.utils import timezone

from django.conf import settings
from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest


class Command(BaseCommand):
    help = (
        "Create a pending special membership request on behalf of a user "
        "using user email and dataset id."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "user_email",
            type=str,
            help="Email of the user for whom the request will be created",
        )
        parser.add_argument(
            "dataset_id",
            type=int,
            help="SpecialMembershipDataset id",
        )
        parser.add_argument(
            "--status",
            type=str,
            default=UserSpecialMembershipRequest.STATUS_PENDING,
            choices=[
                UserSpecialMembershipRequest.STATUS_PENDING,
                UserSpecialMembershipRequest.STATUS_PENDING_TEMPORARY,
                UserSpecialMembershipRequest.STATUS_APPROVED,
                UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY,
                UserSpecialMembershipRequest.STATUS_REJECTED,
                UserSpecialMembershipRequest.STATUS_REVOKED,
            ],
            help=(
                "Initial status of the request "
                f"(default: {UserSpecialMembershipRequest.STATUS_PENDING})"
            ),
        )
        parser.add_argument(
            "--notes",
            type=str,
            default=None,
            help="Optional notes to attach to the request",
        )
        parser.add_argument(
            "--revoke-after",
            type=float,
            default=None,
            dest="revoke_after",
            help="Number of days after which the temporary membership expires (sets temporary_expires_at and overrides the default value from subscription metadata)",
        )

    def handle(
        self, user_email: str, dataset_id: int, *args: Any, **options: Any
    ) -> None:
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist as exc:
            raise CommandError(
                f"User with email '{user_email}' does not exist."
            ) from exc

        try:
            dataset = SpecialMembershipDataset.objects.select_related("reviewer").get(
                pk=dataset_id
            )
        except SpecialMembershipDataset.DoesNotExist as exc:
            raise CommandError(
                f"SpecialMembershipDataset with id={dataset_id} does not exist."
            ) from exc

        revoke_after: float | None = options["revoke_after"]
        # Check that revoke_after options is valid int or float greater than 0
        if revoke_after is not None:
            if revoke_after <= 0:
                raise CommandError(
                    f"Invalid value for --revoke-after: {revoke_after}. It must be a positive number."
                )

        if (
            revoke_after is None
            and options["status"]
            == UserSpecialMembershipRequest.STATUS_APPROVED_TEMPORARY
        ):
            revoke_after = dataset.resolve_temporary_automatic_approval_after_days(
                default_days=settings.IMPRESSO_SPECIAL_MEMBERSHIP_TEMPORARY_APPROVAL_DEFAULT_DAYS
            )

        # normally this would be set from request.creation_date + revoke_after,
        # but since we're creating the request now we can set it from now + revoke_after.
        temporary_expires_at = (
            timezone.now() + timedelta(days=revoke_after)
            if revoke_after is not None
            else None
        )

        try:
            request = UserSpecialMembershipRequest.objects.create(
                user=user,
                reviewer=dataset.reviewer,
                subscription=dataset,
                status=options["status"],
                notes=options["notes"],
                temporary_expires_at=temporary_expires_at,
            )
        except IntegrityError as exc:
            raise CommandError(
                "A request for this user and dataset already exists or could not be created."
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Created special membership request "
                f"id={request.pk} for user='{user.email}' and dataset_id={dataset.pk}."
            )
        )
