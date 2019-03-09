from django.db import models
from django.contrib.auth.models import User
from . import Job, Collection, SearchQuery

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/downloads/user_<id>/<filename>
    return 'attachments/user_{0}/{1}'.format(instance.job.creator.id, filename)

class Attachment(models.Model):
    # id is acomposition of what is expected, so we don't have useless duplicates:
    id = models.CharField(primary_key=True, max_length=50)
    upload = models.FileField(upload_to=user_directory_path)

    date_created       = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    job = models.ForeignKey(Job, on_delete=models.CASCADE)
