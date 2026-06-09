from datetime import timedelta
from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils import timezone

from impresso.models import UserSpecialMembershipRequest


class Command(BaseCommand):
    ANSI_RESET = "\033[0m"
    ANSI_BOLD = "\033[1m"
    ANSI_CYAN = "\033[36m"
    ANSI_YELLOW = "\033[33m"
    ANSI_GREEN = "\033[32m"
    ANSI_RED = "\033[31m"

    help = (
        "Check approved special memberships and revoke access when the related "
        "dataset revokeAfterDays threshold has elapsed."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run the command without making any actual changes to the database.",
        )

    def _get_admin_change_url(self, request_id: int) -> str:
        admin_path = reverse(
            "admin:impresso_userspecialmembershiprequest_change", args=[request_id]
        )
        return urljoin(
            f"{settings.IMPRESSO_BASE_URL.rstrip('/')}/", admin_path.lstrip("/")
        )

    def _format_record_block(
        self,
        req: UserSpecialMembershipRequest,
        dataset_title: str,
        admin_change_url: str,
        detail: str,
    ) -> str:
        return (
            f"  - Request ID: {req.pk}\n"
            f"    User: {req.user.username}\n"
            f"    Dataset: {dataset_title}\n"
            f"    Admin: {admin_change_url}\n"
            f"    Details: {detail}\n"
        )

    def _write_section(self, title: str, color: str, records: list[str]) -> None:
        self.stdout.write(
            f"\n{color}{self.ANSI_BOLD}{title}{self.ANSI_RESET}\n"
            f"{color}{'-' * len(title)}{self.ANSI_RESET}\n"
        )
        if not records:
            self.stdout.write("  (none)\n")
            return
        for record in records:
            self.stdout.write(record)

    def handle(self, *args: Any, **options: Any) -> None:
        dry_run = options.get("dry_run", False)
        now = timezone.now()

        self.stdout.write(
            "\n"
            f"{self.ANSI_BOLD}Special Membership Revocation Audit{self.ANSI_RESET}\n"
            f"  - Dry run: {self.ANSI_BOLD}{dry_run}{self.ANSI_RESET}\n"
            f"  - Base URL: {self.ANSI_BOLD}{settings.IMPRESSO_BASE_URL}{self.ANSI_RESET}\n"
        )

        if dry_run:
            self.stdout.write(self.style.NOTICE("Running in DRY RUN mode."))

        requests = UserSpecialMembershipRequest.objects.filter(
            status=UserSpecialMembershipRequest.STATUS_APPROVED
        ).select_related("user", "subscription")

        total_count = requests.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Found {total_count} special memberships with approved status."
            )
        )

        revokable_requests: list[UserSpecialMembershipRequest] = []
        revocation_needed_blocks: list[str] = []
        active_blocks: list[str] = []
        non_revokable_blocks: list[str] = []

        for req in requests:
            dataset_title = req.subscription.title if req.subscription else "None"
            admin_change_url = self._get_admin_change_url(req.pk)
            revoke_after_days = (
                req.subscription.resolve_revoke_after_days(default_days=None)
                if req.subscription
                else None
            )

            if revoke_after_days is None:
                non_revokable_blocks.append(
                    self._format_record_block(
                        req=req,
                        dataset_title=dataset_title,
                        admin_change_url=admin_change_url,
                        detail=(
                            "ACTIVE, NON-REVOKABLE: "
                            "missing or invalid revokeAfterDays metadata"
                        ),
                    )
                )
                continue

            revoke_at = req.date_created + timedelta(days=revoke_after_days)
            if revoke_at <= now:
                revokable_requests.append(req)
                revocation_needed_blocks.append(
                    self._format_record_block(
                        req=req,
                        dataset_title=dataset_title,
                        admin_change_url=admin_change_url,
                        detail=(
                            "REVOCATION NEEDED: "
                            f"created {req.date_created.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                            f"revokeAfterDays={revoke_after_days}"
                        ),
                    )
                )
                continue

            active_blocks.append(
                self._format_record_block(
                    req=req,
                    dataset_title=dataset_title,
                    admin_change_url=admin_change_url,
                    detail=(
                        "ACTIVE: "
                        f"revokes at {revoke_at.strftime('%Y-%m-%d %H:%M:%S %Z')}, "
                        f"revokeAfterDays={revoke_after_days}"
                    ),
                )
            )

        self.stdout.write(
            "\n"
            f"{self.ANSI_BOLD}Summary{self.ANSI_RESET}\n"
            f"  - REVOCATION NEEDED: {self.ANSI_YELLOW}{len(revocation_needed_blocks)}{self.ANSI_RESET}\n"
            f"  - ACTIVE: {self.ANSI_GREEN}{len(active_blocks)}{self.ANSI_RESET}\n"
            f"  - ACTIVE (NON-REVOKABLE): {self.ANSI_RED}{len(non_revokable_blocks)}{self.ANSI_RESET}\n"
        )

        self._write_section(
            title="REVOCATION NEEDED",
            color=self.ANSI_YELLOW,
            records=revocation_needed_blocks,
        )
        self._write_section(
            title="ACTIVE",
            color=self.ANSI_GREEN,
            records=active_blocks,
        )
        self._write_section(
            title="ACTIVE (NON-REVOKABLE)",
            color=self.ANSI_RED,
            records=non_revokable_blocks,
        )

        if dry_run:
            self.stdout.write(
                self.style.NOTICE(
                    f"Dry run completed: {len(revokable_requests)} revocations need implementation."
                )
            )
            return

        for req in revokable_requests:
            req.status = UserSpecialMembershipRequest.STATUS_REVOKED
            req.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Revoked {len(revokable_requests)} approved special memberships that needed revocation."
            )
        )
        self.stdout.write(
            f"\n{self.ANSI_CYAN}{self.ANSI_BOLD}Done.{self.ANSI_RESET}"
            " Revocation workflow completed.\n"
        )
