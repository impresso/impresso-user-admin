from django.conf import settings
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib.auth.models import User


class UserPlanRequestAdmin(admin.ModelAdmin):
    change_list_template = "admin/change_list.html"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "user-plan-requests/",
                self.admin_site.admin_view(self.user_requests_view),
                name="user-plan-requests",
            ),
        ]
        return custom_urls + urls

    def user_plan_requests_view(self, request):
        # Filter users who are requesting a group (customize the logic as needed)
        requesting_users = User.objects.filter(
            groups__name__in=[
                settings.IMPRESSO_GROUP_USER_PLAN_REQUEST_EDUCATIONAL,
                settings.IMPRESSO_GROUP_USER_PLAN_REQUEST_RESEARCHER,
            ]
        )

        # Reuse the existing change_list template
        context = {
            **self.admin_site.each_context(request),
            "title": "Users requesting a change of Plan",
            "cl": {
                "result_list": requesting_users,
                "opts": User._meta,
            },
        }

        return render(request, "admin/change_list.html", context)
