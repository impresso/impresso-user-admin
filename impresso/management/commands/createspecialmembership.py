import json
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.db import IntegrityError

from impresso.models import SpecialMembershipDataset, UserSpecialMembershipRequest


class Command(BaseCommand):
    help = (
        "Create a pending special membership request for a specific user and dataset."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "sm_dataset_id",
            type=int,
            help="SpecialMembershipDataset id",
        )
        parser.add_argument(
            "username",
            type=str,
            help="Username for which the request will be created",
        )
        parser.add_argument(
            "--notes",
            type=str,
            default=None,
            help="Optional notes to attach to the special membership request",
        )

    def handle(self, sm_dataset_id: int, username: str, *args: Any, **options: Any) -> None:
        notes = options.get("notes")
        self.stdout.write(
            f"Creating special membership request: dataset_id={sm_dataset_id}, username={username}"
        )
        if notes:
            self.stdout.write(f"Notes: {notes}")

        try:
            dataset = SpecialMembershipDataset.objects.select_related("reviewer").get(
                pk=sm_dataset_id
            )
        except SpecialMembershipDataset.DoesNotExist as exc:
            raise CommandError(
                f"SpecialMembershipDataset with id={sm_dataset_id} does not exist."
            ) from exc

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(f"User with username='{username}' does not exist.") from exc

        reviewer = dataset.reviewer
        reviewer_email = reviewer.email if reviewer and reviewer.email else "None"

        try:
            request, created = UserSpecialMembershipRequest.objects.get_or_create(
                user=user,
                subscription=dataset,
                defaults={
                    "reviewer": reviewer,
                    "status": UserSpecialMembershipRequest.STATUS_PENDING,
                    "notes": notes,
                },
            )
        except IntegrityError as exc:
            raise CommandError(
                "Could not create special membership request due to database integrity error."
            ) from exc

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created request id={request.pk} with status='{request.status}'."
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Request already exists for this user and dataset; returning existing record."
                )
            )
            self.stdout.write(
                f"Existing request id={request.pk}, status='{request.status}', reviewer="
                f"'{request.reviewer.username if request.reviewer else 'None'}'"
            )

        self.stdout.write(f"Reviewer email: {reviewer_email}")
        self.stdout.write(
            "Dataset metadata: "
            + json.dumps(dataset.metadata or {}, ensure_ascii=True, sort_keys=True)
        )
