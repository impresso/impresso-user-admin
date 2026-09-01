from django.contrib.auth.models import User
from django.db import models


class BaristaConversation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="barista_conversations",
    )
    barista_session_id = models.CharField(max_length=255, db_index=True)
    label = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)
    date_last_modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_last_modified"]
        verbose_name = "Barista Conversation"
        verbose_name_plural = "Barista Conversations"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.label}"
