import json
from django.db import models
from django.contrib.auth.models import User


class SearchQuery(models.Model):
    """
    Please save as
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=500)
    description = models.TextField()
    data = models.TextField(null=True, blank=True, default=json.dumps([], indent=1))

    creator = models.ForeignKey(User,  on_delete=models.CASCADE);

    date_created       = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'search_queries'
        verbose_name_plural = 'Search Queries'
