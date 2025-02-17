import json
from django.db import models
from django.contrib.auth.models import User


class Job(models.Model):
    BULK_COLLECTION_FROM_QUERY = "BCQ"
    BULK_COLLECTION_FROM_QUERY_TR = "BCT"
    DELETE_COLLECTION = "DCO"
    SYNC_COLLECTION_TO_SOLR = "IDX"
    SYNC_SELECTED_COLLECTABLE_ITEMS_TO_SOLR = "IDL"
    SYNC_COLLECTIONS_TO_SOLR_TR = "ITR"
    EXPORT_COLLECTION_AS_CSV = "EXC"
    EXPORT_QUERY_AS_CSV = "EXP"
    TEST = "TES"
    CREATE_UPLOADED_IMAGE = "IMG"
    REMOVE_FROM_SOLR = "RDX"
    REMOVE_COLLECTIONS_FROM_SOLR_TR = "RTR"
    UPDATE_USER_BITMAP = "UUB"

    TYPE_CHOICES = (
        (BULK_COLLECTION_FROM_QUERY, "Bulk collection from query"),
        (BULK_COLLECTION_FROM_QUERY_TR, "Bulk collection from query TR passages"),
        (DELETE_COLLECTION, "Delete collection"),
        (SYNC_COLLECTION_TO_SOLR, "Index collection in search engine"),
        (
            SYNC_SELECTED_COLLECTABLE_ITEMS_TO_SOLR,
            "Index only collection for a few content items",
        ),  # noqa
        (EXPORT_COLLECTION_AS_CSV, "Export collection as CSV"),
        (EXPORT_QUERY_AS_CSV, "Export query as CSV"),
        (TEST, "10 minutes countdown, 1 percent every 6 seconds"),
        (
            CREATE_UPLOADED_IMAGE,
            "Generate vector signature for the image and store the result in the db",
        ),  # noqa
        (SYNC_COLLECTIONS_TO_SOLR_TR, "Sync coll. to related TR passages"),
        (REMOVE_FROM_SOLR, "Remove collection from solr index"),
        (REMOVE_COLLECTIONS_FROM_SOLR_TR, "Remove coll. from SOLR TR index"),
        (UPDATE_USER_BITMAP, "Update user bitmap"),
    )

    READY = "REA"
    RUN = "RUN"
    DONE = "DON"
    ERR = "ERR"
    ARCHIVED = "ARC"
    STOP = "STO"
    RIP = "RIP"

    STATUS_CHOICES = (
        (READY, "ready"),
        (RUN, "running"),
        (DONE, "Finished, no errors!"),
        (ARCHIVED, "Finished, archived by the user"),
        (STOP, "Please stop"),
        (RIP, "Stopped by user! Rest IN Peace..."),
        (ERR, "Ops, errors!"),
    )

    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default=READY)

    date_created = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    extra = models.TextField(default="{}")

    description = models.TextField(default="")

    def get_progress(self):
        try:
            json.loads(self.extra).get("progress", 0.0)
        except json.JSONDecodeError:
            return 0.0

    class Meta:
        db_table = "jobs"
        verbose_name_plural = "jobs"
