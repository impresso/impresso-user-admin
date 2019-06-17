from django.db import models
from django.contrib.auth.models import User

def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/attachments/user_<id>/uploads/<filename>
    return 'attachments/user_{0}/uploads/{1}'.format(instance.creator.id, filename)


class UploadedImage(models.Model):
    id = models.CharField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    signature = models.TextField()
    md5_checksum = models.CharField(max_length=32, db_index=True)
    thumbnail = models.TextField(default='')

    date_created       = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    creator = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'uploaded_images'
        ordering = ['-date_last_modified']
