from django.db import models
from . import Newspaper

class Issue(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    year = models.IntegerField()
    newspaper = models.ForeignKey(Newspaper, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'issues'
