from django.db import models
from django.contrib.auth.models import User

class Job(models.Model):
    BULK_COLLECTION_FROM_QUERY = 'BCQ'
    DELETE_COLLECTION = 'DCO'
    SYNC_COLLECTION_TO_SOLR = 'IDX'
    EXPORT_COLLECTION_AS_CSV = 'EXP'
    EXPORT_QUERY_AS_CSV = 'EXP'
    TEST = 'TES'

    TYPE_CHOICES = (
        (BULK_COLLECTION_FROM_QUERY, 'Bulk collection from query'),
        (DELETE_COLLECTION, 'Delete collection'),
        (SYNC_COLLECTION_TO_SOLR, 'Index collection in search engine'),
        (EXPORT_COLLECTION_AS_CSV, 'Export collection as CSV'),
        (EXPORT_QUERY_AS_CSV, 'Export query as CSV'),
        (TEST, '10 minutes countdown, 1 percent every 6 seconds'),
    )

    READY = 'REA'
    RUN = 'RUN'
    DONE = 'DON'
    ERR = 'ERR'
    ARCHIVED = 'ARC'
    STOP = 'STO'

    STATUS_CHOICES = (
        (READY, 'ready'),
        (RUN, 'running'),
        (DONE, 'Finished, no errors!'),
        (ARCHIVED, 'Finished, archived by the user'),
        (STOP, 'Please stop'),
        (ERR, 'Ops, errors!'),
    )

    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default=READY)

    date_created       = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    extra = models.TextField()

    def get_task_meta(self, taskname, progress=0.0, extra = {}):
        meta = {
            'task': taskname,
            'progress': progress,
            'job_id': self.pk,
            'job_status': self.status,
            'user_id': self.creator.pk,
            'user_uid': self.creator.profile.uid,
            'extra': extra
        }
        return meta

    class Meta:
        db_table = 'jobs'
        verbose_name_plural = 'jobs'
