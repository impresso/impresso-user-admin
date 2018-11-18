import json
from django.db import models
from django.contrib.auth.models import User


class SearchQuery(models.Model):
    """
    Please save
    SearchQuery.objects.create(id='creatorid-xyzXYZ')
    """
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=500)
    description = models.TextField()
    data = models.TextField(null=True, blank=True, default=json.dumps([], indent=1))

    creator = models.ForeignKey(User,  on_delete=models.CASCADE);

    class Meta:
        db_table = 'search_queries'
