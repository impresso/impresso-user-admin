from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, Issue, Job, Page, Newspaper, SearchQuery, ContentItem
from .models import Collection, CollectableItem, Tag, TaggableItem
from .models import Attachment

@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('id', 'year', 'newspaper',)
    search_fields = ['id']

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('id', 'newspaper', 'ocr_quality',)
    search_fields = ['id']

@admin.register(Newspaper)
class NewspaperAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'start_year', 'end_year',)
    search_fields = ['title']

@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'name',)

@admin.register(ContentItem)
class ContentItemAdmin(admin.ModelAdmin):
    search_fields = ['id']
    autocomplete_fields = ('newspaper', 'issue',)

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    search_fields = ['name', 'creator']
    list_display = ('id', 'creator', 'name', 'status',)

@admin.register(CollectableItem)
class CollectableItemAdmin(admin.ModelAdmin):
    list_display = ('item_id', 'collection', 'content_type', 'date_added',)
    autocomplete_fields = ('collection',)

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ['name']
    list_display = ('id', 'creator', 'name',)

@admin.register(TaggableItem)
class TaggableItemAdmin(admin.ModelAdmin):
    list_display = ('item_id', 'tag', 'content_type', 'date_added',)
    autocomplete_fields = ('tag',)


class AttachmentInline(admin.StackedInline):
    model = Attachment
    can_delete = True
    verbose_name_plural = 'attachments'
    #
    # def get_readonly_fields(self, request, user=None):
    #     if hasattr(user, 'profile'):
    #         return ['uid',]
    #     else:
    #         return []

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    inlines = (AttachmentInline,)
    list_display = ('id', 'creator', 'type', 'date_created', 'status',)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'profiles'

    def get_readonly_fields(self, request, user=None):
        if hasattr(user, 'profile'):
            return ['uid',]
        else:
            return []


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)
    list_display = ('username', 'uid', 'is_staff',)

    def uid(self, user):
        return user.profile.uid if hasattr(user, 'profile') else None
    uid.short_description = 'short unique identifier'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
