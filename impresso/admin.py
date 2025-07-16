from django.contrib import admin
from django.contrib import messages
from unfold.admin import ModelAdmin  # type: ignore
from django.contrib.auth.models import User
from django.utils.translation import ngettext
from django.utils import timezone
from .models import Issue, Job, Page, Newspaper
from .models import SearchQuery, ContentItem
from .models import Collection, CollectableItem, Tag, TaggableItem
from .models import Attachment, UploadedImage
from .models import UserBitmap, DatasetBitmapPosition, UserRequest


from django.utils.html import format_html
from .views.admin.user_admin import UserAdmin
from .views.admin.user_change_plan_request_admin import UserChangePlanRequestAdmin


@admin.register(UserRequest)
class UserRequestAdmin(ModelAdmin):
    list_display = (
        "user",
        "reviewer",
        "subscription",
        "status",
        "date_created",
    )
    search_fields = ["user__username", "subscription__name"]
    list_filter = ["status"]
    autocomplete_fields = ["user", "reviewer", "subscription"]


@admin.register(UserBitmap)
class UserBitmapAdmin(ModelAdmin):
    list_display = (
        "user",
        "bitmap_display",
        "user_plan_display",
        "num_subscriptions",
        "date_accepted_terms",
    )
    search_fields = ["user__username", "user__email"]
    actions = ["set_terms_accepted_date"]

    def num_subscriptions(self, obj):
        return obj.subscriptions.count()

    def bitmap_display(self, obj):
        if obj.bitmap is None:
            return ""
        return bin(obj.get_bitmap_as_int())

    def user_plan_display(self, obj):
        return obj.get_user_plan()

    @admin.action(description="Accept the terms of use for selected users")
    def set_terms_accepted_date(self, request, queryset):
        # for each user, do a proper save
        updated = queryset.count()
        for user_bitmap in queryset:
            user_bitmap.date_accepted_terms = timezone.now()
            user_bitmap.save()
        self.message_user(
            request,
            ngettext(
                "%d user accepted the terms of use.",
                "%d users accepted the terms of use.",
                updated,
            )
            % updated,
            messages.SUCCESS,
        )

    user_plan_display.short_description = "User Plan"  # type: ignore[attr-defined]


@admin.register(DatasetBitmapPosition)
class DatasetBitmapPositionAdmin(ModelAdmin):
    list_display = ("name", "bitmap_position", "reviewer")
    search_fields = ["name", "reviewer__username", "reviewer__email"]
    readonly_fields = ("bitmap_position",)
    autocomplete_fields = ["reviewer"]


@admin.register(Issue)
class IssueAdmin(ModelAdmin):
    list_display = (
        "id",
        "year",
        "newspaper",
    )
    search_fields = ["id"]


@admin.register(Page)
class PageAdmin(ModelAdmin):
    list_display = (
        "id",
        "newspaper",
        "ocr_quality",
    )
    search_fields = ["id"]


@admin.register(Newspaper)
class NewspaperAdmin(ModelAdmin):
    list_display = (
        "id",
        "title",
        "start_year",
        "end_year",
    )
    search_fields = ["title"]


@admin.register(SearchQuery)
class SearchQueryAdmin(ModelAdmin):
    list_display = (
        "id",
        "creator",
        "description",
        "date_created",
    )


@admin.register(ContentItem)
class ContentItemAdmin(ModelAdmin):
    search_fields = ["id"]
    autocomplete_fields = (
        "newspaper",
        "issue",
    )


@admin.register(Collection)
class CollectionAdmin(ModelAdmin):
    search_fields = ["name", "creator__username", "id"]
    list_display = (
        "id",
        "creator",
        "name",
        "status",
        "date_created",
    )
    ordering = ("-date_created",)
    readonly_fields = (
        "date_created",
        "date_last_modified",
    )


@admin.register(CollectableItem)
class CollectableItemAdmin(ModelAdmin):
    list_display = (
        "item_id",
        "collection",
        "content_type",
        "date_added",
    )
    autocomplete_fields = ("collection",)


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    search_fields = ["name"]
    list_display = (
        "id",
        "creator",
        "name",
    )


@admin.register(TaggableItem)
class TaggableItemAdmin(ModelAdmin):
    list_display = (
        "item_id",
        "tag",
        "content_type",
        "date_added",
    )
    autocomplete_fields = ("tag",)


@admin.register(UploadedImage)
class UploadImageAdmin(ModelAdmin):
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
class JobAdmin(ModelAdmin):
    inlines = (AttachmentInline,)
    search_fields = ["creator__id", "creator__username"]
    list_filter = ["status", "type"]
    show_facets = admin.ShowFacets.ALWAYS
    search_help_text = "Search by creator id (numeric) or username"
    list_display = (
        "id",
        "creator",
        "type",
        "description",
        "date_created",
        "status",
        "attachment",
    )


admin.site.unregister(User)
admin.site.register(User, UserAdmin)
