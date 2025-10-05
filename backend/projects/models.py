from django.db import models
from django.conf import settings
import uuid


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=30, null=False, blank=False)
    description = models.CharField(max_length=150, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="owned_projects",
        on_delete=models.CASCADE
    )
    supervisors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="supervised_projects",
        blank=True
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="member_projects",
        blank=True
    )
    chat = models.OneToOneField(
        "chat.Chat",
        on_delete=models.CASCADE,
        null=True
    )
    attached_files = models.ManyToManyField(
        'common.File',
        blank=True
    )
    create_date = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    finish_date = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class Phase(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(Project, related_name="phases", on_delete=models.CASCADE)
    title = models.CharField(max_length=30, null=False, blank=False)
    description = models.CharField(max_length=150, blank=True)
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="member_phases",
        blank=True
    )
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("InProgress", "In Progress"),
        ("Completed", "Completed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=False, blank=False, default="Pending")
    picked_color = models.CharField(max_length=7, null=False, blank=False, default="#FFFFFF")
    begin_date = models.DateTimeField(null=False, blank=False)
    end_date = models.DateTimeField(null=False, blank=False)

    def __str__(self):
        return f"{self.project.title} - {self.title}"