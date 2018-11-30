import json
from django.db import models
from django.contrib.auth.models import User

class Bucket(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=500)
    description = models.TextField()
    date_created       = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        abstract = True
        ordering = ['name']
        unique_together = ("name", "creator")
