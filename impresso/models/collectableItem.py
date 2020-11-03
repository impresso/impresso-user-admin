from django.db import models
from . import Collection, SearchQuery


class CollectableItem(models.Model):
    ARTICLE = 'A'
    PAGE = 'P'
    ISSUE = 'I'
    IMAGE = 'M'

    CONTENT_TYPE_CHOICES = (
        (ARTICLE, 'Article'),
        (PAGE, 'Page'),
        (ISSUE, 'Issue'),
        (IMAGE, 'Image'),
    )

    item_id = models.CharField(max_length=50, db_index=True)
    item_date = models.DateField(null=True)
    content_type = models.CharField(max_length=1, choices=CONTENT_TYPE_CHOICES)
    date_added = models.DateTimeField(auto_now_add=True, db_index=True)
    indexed = models.BooleanField(default=False, db_index=True)
    # Foreing key: the collection
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    # Foreing key: the search query if any when the item was added
    search_query = models.ForeignKey(
        SearchQuery, null=True, blank=True,
        verbose_name="search query", on_delete=models.SET_NULL)
    search_query_score = models.FloatField(
        default=0.0, null=True, blank=True, db_index=True)

    class Meta:
        db_table = 'collectable_items'
        unique_together = ("item_id", "collection")
