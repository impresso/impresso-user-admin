from django.contrib import admin
from .models import Newspaper

@admin.register(Newspaper)
class NewspaperAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'start_year', 'end_year',)
