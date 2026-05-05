from typing import Any

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError

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

    def handle(self, user_email: str, dataset_id: int, *args: Any, **options: Any) -> None:
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist as exc:
            raise CommandError(f"User with email '{user_email}' does not exist.") from exc

        try:
            dataset = SpecialMembershipDataset.objects.select_related("reviewer").get(
                pk=dataset_id
            )
        except SpecialMembershipDataset.DoesNotExist as exc:
            raise CommandError(
                f"SpecialMembershipDataset with id={dataset_id} does not exist."
            ) from exc

        try:
            request = UserSpecialMembershipRequest.objects.create(
                user=user,
                reviewer=dataset.reviewer,
                subscription=dataset,
                status=UserSpecialMembershipRequest.STATUS_PENDING,
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