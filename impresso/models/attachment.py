import uuid
from django.core.files.base import ContentFile
from django.db import models
from django.contrib.auth.models import User
from . import Job, Collection, SearchQuery


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/downloads/user_<id>/<filename>
    return "attachments/user_{0}/{1}".format(instance.job.creator.id, filename)


class Attachment(models.Model):
    """
    See https://docs.djangoproject.com/en/2.1/topics/db/examples/one_to_one/
    """

    job = models.OneToOneField(Job, on_delete=models.CASCADE, primary_key=True)
    upload = models.FileField(upload_to=user_directory_path)

    date_created = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    # optional links
    search_query = models.ForeignKey(
        SearchQuery, null=True, blank=True, on_delete=models.CASCADE
    )
    collection = models.ForeignKey(
        Collection, null=True, blank=True, on_delete=models.CASCADE
    )

    def generate_filename(self, extension=".txt"):
        filename_uid = uuid.uuid3(uuid.NAMESPACE_URL, str(self.pk)).hex[:8]
        filename_date = self.date_created.strftime("%Y-%m-%d")
        return f"{filename_date}-{filename_uid}.{extension}"

    @staticmethod
    def create_from_job(job, extension="txt"):
        attachment = Attachment.objects.create(job=job)
        attachment.upload.save(attachment.generate_filename(extension), ContentFile(""))
        return attachment

    class Meta:
        db_table = "attachments"
        verbose_name_plural = "attachments"
