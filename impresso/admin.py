from django import forms
from django.contrib import admin
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import ValidationError
from unfold.admin import ModelAdmin  # type: ignore
from django.contrib.auth.models import User
from django.utils.translation import ngettext
from django.utils import timezone
from django.utils.html import format_html
from impresso.models.userBitmapSubscription import UserBitmapSubscription
from .models import Issue, Job, Page, Newspaper
from .models import SearchQuery, ContentItem
from .models import Collection, CollectableItem, Tag, TaggableItem
from .models import Attachment, UploadedImage
from .models import UserBitmap, SpecialMembershipDataset, UserSpecialMembershipRequest

from .views.admin.user_admin import UserAdmin
from .views.admin.user_change_plan_request_admin import UserChangePlanRequestAdmin


@admin.register(UserSpecialMembershipRequest)
class UserSpecialMembershipRequestAdmin(ModelAdmin):
    list_display = (
        "user",
        "reviewer",
        "subscription",
        "status",
        "date_created",
        "date_last_modified",
        "temporary_expires_at",
    )
    search_fields = ["user__username", "subscription__title"]
    list_filter = ["status"]
    autocomplete_fields = ["user", "reviewer", "subscription"]


@admin.register(UserBitmapSubscription)
class UserBitmapSubscriptionAdmin(ModelAdmin):
    list_display = (
        "userbitmap__user__username",
        "specialmembershipdataset",
    )
    autocomplete_fields = ["userbitmap"]


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


class SpecialMembershipDatasetAdminForm(forms.ModelForm):

    class Meta:
        model = SpecialMembershipDataset
        fields = "__all__"
        help_texts = {
            "metadata": format_html(
                "<b>Allowed Values</b>: <pre>{}</pre><br><b>Note</b>: revokeAfterDays is working only if enableTemporaryAutomaticAcceptance is set to true.",
                ", ".join(sorted(SpecialMembershipDataset.METADATA_ALLOWED_KEYS)),
            ),
        }

    def clean_metadata(self) -> dict:
        metadata = self.cleaned_data.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValidationError("Metadata must be a JSON object.")

        allowed_keys = SpecialMembershipDataset.METADATA_ALLOWED_KEYS
        extra_keys = set(metadata.keys()) - allowed_keys
        if extra_keys:
            raise ValidationError(
                f"Unknown metadata key(s): {', '.join(sorted(extra_keys))}. Allowed key(s) are: {', '.join(sorted(allowed_keys))}."
            )

        modality = metadata.get("modality")
        if modality is not None:
            if not isinstance(modality, str):
                raise ValidationError("metadata.modality must be a string.")

            allowed_modalities = {
                settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_CC_REVIEWER,
                settings.IMPRESSO_EMAIL_MODALITY_SPECIAL_MEMBERSHIP_REQUEST_NOTIFY_REVIEWER,
            }
            if modality not in allowed_modalities:
                allowed = ", ".join(sorted(allowed_modalities))
                raise ValidationError(f"metadata.modality must be one of: {allowed}.")
        enable_temporary_automatic_acceptance = metadata.get(
            "enableTemporaryAutomaticAcceptance"
        )
        if enable_temporary_automatic_acceptance is not None and not isinstance(
            enable_temporary_automatic_acceptance, bool
        ):
            raise ValidationError(
                "metadata.enableTemporaryAutomaticAcceptance must be a boolean."
            )
        revoke_after_days = metadata.get("revokeAfterDays")
        if revoke_after_days is not None:
            if not isinstance(revoke_after_days, (int, float)):
                raise ValidationError(
                    "metadata.revokeAfterDays must be an integer or float."
                )
            if revoke_after_days <= 0:
                raise ValidationError(
                    "metadata.revokeAfterDays must be a positive integer or float."
                )
        return metadata


@admin.register(SpecialMembershipDataset)
class SpecialMembershipDatasetAdmin(ModelAdmin):
    list_display = (
        "title",
        "bitmap_position",
        "reviewer",
        "modality",
        "enable_temporary_automatic_acceptance",
        "revoke_after_days_display",
    )
    search_fields = ["title", "reviewer__username", "reviewer__email"]
    readonly_fields = ("bitmap_position",)
    autocomplete_fields = ["reviewer"]
    form = SpecialMembershipDatasetAdminForm

    @admin.display(description="Revoke after")
    def revoke_after_days_display(self, obj: SpecialMembershipDataset) -> str:
        days = obj.revoke_after_days
        if days is None:
            return "-"
        total_minutes = round(days * 24 * 60)
        parts = []
        years, remainder = divmod(total_minutes, 365 * 24 * 60)
        if years:
            parts.append(f"{years}y")
        months, remainder = divmod(remainder, 30 * 24 * 60)
        if months:
            parts.append(f"{months}mo")
        weeks, remainder = divmod(remainder, 7 * 24 * 60)
        if weeks:
            parts.append(f"{weeks}w")
        day_part, remainder = divmod(remainder, 24 * 60)
        if day_part:
            parts.append(f"{day_part}d")
        hours, minutes = divmod(remainder, 60)
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        return format_html(
            (
                f"<b>{obj.revoke_after_days}</b> days <br/> " + " ".join(parts)
                if parts
                else "0m"
            ),
        )


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
