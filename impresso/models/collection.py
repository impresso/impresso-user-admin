import json
from django.db import models
from django.contrib.auth.models import User
from . import Bucket



class Collection(Bucket):
    """
    Please save as
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """
    STATUS_CHOICES = (
        ('PRI', 'Private'),
        ('SHA', 'Publicly available - only with a link'),
        ('PUB', 'Public and indexed'),
    )

    status = models.CharField(max_length=3, choices=STATUS_CHOICES)

    def __str__(self):
        return self.name

    class Meta(Bucket.Meta):
        db_table = 'collections'
        verbose_name_plural = 'collections'
