from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.translation import ngettext

from .models import Profile, Issue, Job, Page, Newspaper
from .models import SearchQuery, ContentItem
from .models import Collection, CollectableItem, Tag, TaggableItem
from .models import Attachment, UploadedImage

from impresso.tasks import after_user_activation


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "year",
        "newspaper",
    )
    search_fields = ["id"]


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "newspaper",
        "ocr_quality",
    )
    search_fields = ["id"]


@admin.register(Newspaper)
class NewspaperAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "start_year",
        "end_year",
    )
    search_fields = ["title"]


@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "creator",
        "description",
        "date_created",
    )


@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    search_fields = ["id"]
    autocomplete_fields = (
        "newspaper",
        "issue",
    )


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    search_fields = ["name", "creator", "id"]
    list_display = (
        "id",
        "creator",
        "name",
        "status",
        "date_created",
    )
    readonly_fields = (
        "date_created",
        "date_last_modified",
    )


@admin.register(CollectableItem)
class CollectableItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_id",
        "collection",
        "content_type",
        "date_added",
    )
    autocomplete_fields = ("collection",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]
    list_display = (
        "id",
        "creator",
        "name",
    )


@admin.register(TaggableItem)
class TaggableItemAdmin(admin.ModelAdmin):
    list_display = (
        "item_id",
        "tag",
        "content_type",
        "date_added",
    )
    autocomplete_fields = ("tag",)


@admin.register(UploadedImage)
class UploadImageAdmin(admin.ModelAdmin):
    list_display = ("id", "creator", "name", "date_last_modified")


class AttachmentInline(admin.StackedInline):
    model = Attachment
    can_delete = True
    verbose_name_plural = "attachments"
    #
    # def get_readonly_fields(self, request, user=None):
    #     if hasattr(user, 'profile'):
    #         return ['uid',]
    #     else:
    #         return []


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    inlines = (AttachmentInline,)
    search_fields = ["creator__id", "creator__username"]
    list_filter = ["status", "type"]
    show_facets = admin.ShowFacets.ALWAYS
    list_display = (
        "id",
        "creator",
        "type",
        "description",
        "date_created",
        "status",
        "attachment",
    )


class ProfileInline(admin.StackedInline):
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


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = (
        "username",
        "uid",
        "is_staff",
        "is_active",
        "email",
        "date_joined",
        "last_login",
    )
    actions = ["make_active", "make_suspended"]

    @admin.action(description="ACTIVATE selected users")
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

    @admin.action(description="SUSPEND selected users")
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

    uid.short_description = "short unique identifier"


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
