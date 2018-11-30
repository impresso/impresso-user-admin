from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import Profile, Issue, Newspaper, SearchQuery, ContentItem, Collection, Tag, CollectableItem



@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ('id', 'year',)
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
    list_display = ('id', 'creator', 'name',)
    autocomplete_fields = ('content_items',)


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
