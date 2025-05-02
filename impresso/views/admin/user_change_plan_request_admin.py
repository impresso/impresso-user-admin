from django.contrib import admin, messages
from django.utils.translation import ngettext
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from impresso.models import UserChangePlanRequest
from impresso.utils.models.user import get_plan_from_group_name


@admin.register(UserChangePlanRequest)
class UserChangePlanRequestAdmin(ModelAdmin):
    search_fields = ["user__username", "user__last_name"]
    list_filter = ["status"]
    search_help_text = "Search by requester user id (numeric) or username"
    list_display = (
        "user",
        "plan_as_html",
        "status_as_html",
        "date_created",
        "date_last_modified",
        "changelog_parsed",
    )
    autocomplete_fields = ["user", "plan"]
    actions = ["approve_requests", "reject_requests"]

    def plan_as_html(self, obj: UserChangePlanRequest) -> str:
        try:
            return get_plan_from_group_name(obj.plan)[0]
        except AttributeError:
            return "Plan not found"

    def status_as_html(self, obj: UserChangePlanRequest) -> str:
        """
        Returns an HTML string representing the status of a UserChangePlanRequest with appropriate styling based on its status.
        """
        # When Rejected bg-red-500 outline-red-200 dark:outline-red-500/20
        # When Approved bg-green-500 outline-green-200 dark:outline-green-500/20
        # When Pending bg-primary-500 outline-primary-200 dark:outline-yellow-500/20
        coloured_class = "bg-orange-500 outline-orange-200/20 dark:outline-orange-500/20 text-orange-600"
        if obj.status == UserChangePlanRequest.STATUS_APPROVED:
            coloured_class = "bg-green-500 outline-green-200 dark:outline-green-500/20"
        elif obj.status == UserChangePlanRequest.STATUS_REJECTED:
            coloured_class = "bg-red-500 outline-red-200 dark:outline-red-500/20"

        return format_html(
            f"""
              <div class="flex items-center ">
                <div class="block mr-3 outline rounded-full ml-1 h-1 w-1 {coloured_class}"></div>
                <span>
                  {obj.get_status_display()}
                </span>
              </div>
              """,
            coloured_class,
        )

    status_as_html.short_description = "Status"  # type: ignore[attr-defined]

    def changelog_parsed(self, obj):
        try:
            html = "<ul style='padding:0'>"
            # reverse changelog order
            for index, entry in enumerate(obj.changelog[::-1]):

                plan_label, _ = get_plan_from_group_name(entry["plan"])
                date = timezone.datetime.fromisoformat(entry["date"]).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                if index == 0:

                    html += f"""
                      <li
                        class="px-2 py-2 border  bg-white font-medium border-base-500 rounded shadow-sm"
                      >Request for: <b>{plan_label}</b><br/>{date} <b>{entry['status']}</b></li>"""
                else:
                    html += f"<li class='px-2 py-1'>Request for: {plan_label}<br/>{date} ({entry['status']})</li>"
            html += "</ul>"
            return format_html(html)
        except AttributeError as e:
            return f"Changelog error: {e}"
        except (TypeError, ValueError):
            return "Invalid JSON"

    changelog_parsed.short_description = "Changes"  # type: ignore[attr-defined]

    @admin.action(description="APPROVE selected requests")
    def approve_requests(self, request, queryset):
        updated = queryset.count()
        for req in queryset:
            req.status = UserChangePlanRequest.STATUS_APPROVED
            # post_save method  in impresso.signals already include the code to add the user the Plan Group.
            req.save()
        self.message_user(
            request,
            ngettext(
                "%d request was successfully approved.",
                "%d requests were successfully approved.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @admin.action(description="REJECT selected requests")
    def reject_requests(self, request, queryset):
        updated = queryset.count()
        for req in queryset:
            req.status = UserChangePlanRequest.STATUS_REJECTED
            # post_save() method in impresso.signals already includes the code to remove the Plan Group.
            req.save()
        self.message_user(
            request,
            ngettext(
                "%d request was successfully rejected.",
                "%d requests were successfully rejected.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )
