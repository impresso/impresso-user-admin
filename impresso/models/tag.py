import json
from django.db import models
from django.contrib.auth.models import User
from . import Bucket, ContentItem

class Tag(Bucket):
    """
    Please save as
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """
    class Meta(Bucket.Meta):
        db_table = 'tags'
        verbose_name_plural = 'tags'
