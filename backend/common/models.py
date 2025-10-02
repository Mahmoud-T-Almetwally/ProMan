from django.db import models
from django.conf import settings
import uuid


class File(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, null=False, blank=False)
    type = models.CharField(max_length=100, null=False, blank=False)
    size = models.IntegerField()
    file = models.FileField(upload_to='uploads/') # The actual file field
    upload_date = models.DateTimeField(auto_now_add=True)
    uploader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    def __str__(self):
        return self.name