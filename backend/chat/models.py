from django.db import models
from django.conf import settings
import uuid


class Chat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def __str__(self):
        return str(self.id)

class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    chat = models.ForeignKey(Chat, related_name="messages", on_delete=models.CASCADE) 
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="sent_messages",
        on_delete=models.CASCADE
    )
    send_date = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=300, null=False, blank=False)
    attached = models.ManyToManyField(
        "common.File",
        blank=True
    )

    def __str__(self):
        return f"Message from {self.sender.username} in chat {self.chat.id}"