from django.db import models
from django.contrib.auth.models import User

class Job(models.Model):
    BULK_COLLECTION_FROM_QUERY = 'BCQ'

    TYPE_CHOICES = (
        (BULK_COLLECTION_FROM_QUERY, 'Bulk collection from query'),
    )

    READY = 'REA'
    RUN = 'RUN'
    DONE = 'DON'
    ERR = 'ERR'
    ARCHIVED = 'ARC'

    STATUS_CHOICES = (
        (READY, 'ready'),
        (RUN, 'running'),
        (DONE, 'Finished, no errors!'),
        (ARCHIVED, 'Finished, archived by the user'),
        (ERR, 'Ops, errors!'),
    )

    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default=READY)

    date_created       = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    extra = models.TextField()

    class Meta:
        db_table = 'jobs'
        verbose_name_plural = 'jobs'
