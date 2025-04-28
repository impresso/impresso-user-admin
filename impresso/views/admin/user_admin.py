from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.contrib import messages
from impresso.models import Profile
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import StackedInline # type: ignore
from unfold.admin import ModelAdmin # type: ignore
from unfold.decorators import action # type: ignore
from django.conf import settings
from impresso.tasks import after_user_activation
from django.utils.translation import ngettext
from django.urls import path
from django.shortcuts import render, redirect, get_object_or_404
from impresso.utils.models.user import get_plan_from_user_groups 



class GroupFilter(admin.SimpleListFilter):
    title = "Group"
    parameter_name = "group"

    def lookups(self, request, model_admin):
        groups = Group.objects.all()
        return [(group.id, group.name) for group in groups]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(groups__id=self.value())
        return queryset


class ProfileInline(StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "profiles"

    def get_readonly_fields(self, request, user=None):
        if hasattr(user, "profile"):
            return [
                "uid",
            ]
        else:
            return []

from django.views.generic import TemplateView
from unfold.views import UnfoldModelAdminViewMixin

class ToggleStatus(UnfoldModelAdminViewMixin, TemplateView):
    title = "Custom Title"  # required: custom page header title
    permission_required = () # required: tuple of permissions
    template_name = "admin/users/toggle_status.html"
    model_admin = None  # this will be injected via `as_view(model_admin=self)`

    def dispatch(self, request, *args, **kwargs):
        self.user_id = kwargs.get("user_id")
        return super().dispatch(request, *args, **kwargs)
    
    def get(self, request, *args, **kwargs):
        target_user = get_object_or_404(self.model_admin.model, pk=self.user_id)
         # get plan from its groups 
        plan_label, plan_group_name = get_plan_from_user_groups(target_user)
        context = {
            **self.model_admin.admin_site.each_context(request),  # 👈 gets admin site context
            "user": request.user,
            "target_user": target_user,
            "plan_label": plan_label,
            "opts": self.model_admin.model._meta,  # 👈 used in Unfold for headers/breadcrumbs
            "has_view_permission": self.model_admin.has_view_permission(request),
        }

        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(self.model_admin.model, pk=self.user_id)
        user.is_active = not user.is_active
        user.save()
        #  the form has two submits: name="activation_mode" value="receipt" and name="activation_mode" value="silently"
        if user.is_active and request.POST.get("activation_mode") == "receipt":
            # send email!
            after_user_activation.delay(user_id=user.pk)
            messages.success(request, "User status toggled to active, email sent.")
        elif user.is_active and request.POST.get("activation_mode") == "silently":
            # DO NOT SEND EMAIL
            messages.success(request, "User status toggled to active, no email sent.")
        else:
            messages.success(request, f"User status toggled to {'active' if user.is_active else 'inactive'}.")
        return redirect("admin:auth_user_change", object_id=self.user_id)
    

class UserAdmin(ModelAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "uid",
        "is_staff",
        "is_active",
        "email",
        "date_joined",
        "last_login",
        "max_loops_allowed",
        "max_parallel_jobs",
    )
    actions = [
        "make_active",
        "make_suspended",
        "remove_from_group__no_redaction",
        "add_to_group__no_redaction",
    ]
    search_fields = ["username", "profile__uid", "email"]
    list_filter = (GroupFilter, "is_staff", "is_active")
    ordering = ("-date_joined",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:user_id>/toggle-status/",
                self.admin_site.admin_view( ToggleStatus.as_view(model_admin=self)),
                name="user_toggle_status",
            ),
        ]
        return custom_urls + urls

    @action(description="BEWARE! Add selected users to No Redaction group")
    def add_to_group__no_redaction(modeladmin, request, queryset):
        group_name = settings.IMPRESSO_GROUP_USER_PLAN_NO_REDACTION
        try:
            group, created = Group.objects.get_or_create(name=group_name)
            added_count = 0
            for user in queryset:
                if group not in user.groups.all():
                    user.groups.add(group)
                    added_count += 1
            messages.success(request, f"Added {added_count} users to '{group_name}'.")
        except Exception as e:
            messages.error(request, f"Error adding users to '{group_name}': {e}")

    @action(description="Detach selected users from No Redaction group")
    def remove_from_group__no_redaction(modeladmin, request, queryset):
        group_name = (
            settings.IMPRESSO_GROUP_USER_PLAN_NO_REDACTION
        )  # Change this to your actual group name
        try:
            group = Group.objects.get(name=group_name)
            removed_count = 0
            for user in queryset:
                if group in user.groups.all():
                    user.groups.remove(group)
                    removed_count += 1
            messages.success(
                request, f"Removed {removed_count} users from '{group_name}'."
            )
        except Group.DoesNotExist:
            messages.error(request, f"Group '{group_name}' does not exist.")

    @action(description="ACTIVATE selected users")
    def make_active(self, request, queryset):
        updated = queryset.update(is_active=True)
        # send email!
        for user in queryset:
            after_user_activation.delay(user_id=user.pk)
        self.message_user(
            request,
            ngettext(
                "%d user was successfully activated.",
                "%d users were successfully activated.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    @action(description="SUSPEND selected users")
    def make_suspended(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            ngettext(
                "%d user was successfully SUSPENDED. No email has been sent.",
                "%d users were successfully SUSPENDED. No email has been sent.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    def uid(self, user):
        return user.profile.uid if hasattr(user, "profile") else None

    def max_loops_allowed(self, user):
        return user.profile.max_loops_allowed if hasattr(user, "profile") else None

    def max_parallel_jobs(self, user):
        return user.profile.max_parallel_jobs if hasattr(user, "profile") else None

    uid.short_description = "short unique identifier"  # type: ignore[attr-defined]
    max_loops_allowed.short_description = "max loops"  # type: ignore[attr-defined]
    max_parallel_jobs.short_description = "max parallel jobs"  # type: ignore[attr-defined]
