from django.contrib import admin
from .models import Issue, Newspaper, SearchQuery, ContentItem, Collection


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
    list_display = ('id', 'creator', 'name', 'status',)
    autocomplete_fields = ('content_items',)
