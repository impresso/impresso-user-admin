from django.db import models
from . import Issue, Newspaper

class ContentItem(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    newspaper = models.ForeignKey(Newspaper, models.DO_NOTHING)
    issue = models.ForeignKey(Issue, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'content_items'
