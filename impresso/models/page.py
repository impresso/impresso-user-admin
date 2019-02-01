from django.db import models
from . import Newspaper, Issue

class Page(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    newspaper = models.ForeignKey(Newspaper, models.DO_NOTHING)
    issue = models.ForeignKey(Issue, models.DO_NOTHING)

    is_corrupted = models.BooleanField(default=False, db_column='has_corrupted_json')
    is_converted = models.BooleanField(default=False, db_column='has_converted_coordinates')

    n_tokens = models.PositiveIntegerField(default=0)
    
    ocr_quality = models.FloatField(default=0.0)

    class Meta:
        managed = False
        db_table = 'pages'
