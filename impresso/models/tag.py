import json
from django.db import models
from django.contrib.auth.models import User
from . import Bucket, ContentItem

class Tag(Bucket):
    """
    Please save as
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """
    content_items = models.ManyToManyField(ContentItem, verbose_name="content items")

    class Meta(Bucket.Meta):
        db_table = 'tags'
        verbose_name_plural = 'tags'
