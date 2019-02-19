import json
from django.db import models
from django.contrib.auth.models import User
from . import Tag


class TaggableItem(models.Model):
    ARTICLE = 'A'
    PAGE = 'P'
    ISSUE = 'I'

    CONTENT_TYPE_CHOICES = (
        (ARTICLE, 'Article'),
        (PAGE, 'Page'),
        (ISSUE, 'Issue'),
    )

    item_id = models.CharField(max_length=50, db_index=True)
    content_type = models.CharField(max_length=1, choices=CONTENT_TYPE_CHOICES)
    date_added = models.DateTimeField(auto_now_add=True)
    # Foreing key: the collection
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'taggable_items'
        unique_together = ("item_id", "tag")
