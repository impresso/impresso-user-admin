from django.contrib import admin
from .models import Newspaper, SearchQuery

@admin.register(Newspaper)
class NewspaperAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'start_year', 'end_year',)

@admin.register(SearchQuery)
class SearchQueryAdmin(admin.ModelAdmin):
    list_display = ('id', 'creator', 'name')
