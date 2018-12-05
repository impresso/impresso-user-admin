import json
from django.db import models
from django.contrib.auth.models import User
from . import Collection, SearchQuery


class CollectableItem(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('A', 'Article'),
        ('P', 'Page'),
        ('I', 'Issue'),
    )

    item_id = models.CharField(max_length=50)
    content_type = models.CharField(max_length=1, choices=CONTENT_TYPE_CHOICES)
    date_added = models.DateTimeField(auto_now_add=True)
    # Foreing key: the collection
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    # Foreing key: the search query if any when the item was added
    search_query = models.ForeignKey(SearchQuery, null=True, blank=True, verbose_name="search query", on_delete=models.SET_NULL)

    class Meta:
        db_table = 'collectable_items'
        unique_together = ("item_id", "collection")
