from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    username = models.CharField(max_length=20, null=False, blank=False, unique=True)
    email = models.EmailField(null=False, blank=False, unique=True)
    profile_image = models.ForeignKey(
        'common.File',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,  
        on_delete=models.CASCADE,
        related_name='notifications' 
    )
    content = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    create_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.recipient.username}"