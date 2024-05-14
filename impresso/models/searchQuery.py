import json, uuid
from django.db import models
from django.contrib.auth.models import User


class SearchQuery(models.Model):
    """
    Please save as
    SearchQuery.objects.create(id=SearchQuery.generate_id(creator_id=123, query='*:*'), creator_id=123)
    """
    id = models.CharField(primary_key=True, max_length=50)
    hash = models.CharField(max_length=200, null=True, blank=True)
    name = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    data = models.TextField(null=True, blank=True)

    creator = models.ForeignKey(User, on_delete=models.CASCADE);

    date_created       = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    count_items = models.PositiveIntegerField(default=0)

    @staticmethod
    def generate_id(creator_id, query):
        return uuid.uuid3(uuid.NAMESPACE_URL, '{0}/{1}'.format(creator_id, query)).hex

    class Meta:
        db_table = 'search_queries'
        verbose_name_plural = 'Search Queries'
