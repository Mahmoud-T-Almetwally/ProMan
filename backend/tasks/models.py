from django.db import models
from projects.models import Phase
from django.conf import settings
import uuid


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phase = models.ForeignKey(Phase, related_name="tasks", on_delete=models.CASCADE)
    title = models.CharField(max_length=30, null=False, blank=False)
    description = models.CharField(max_length=150, blank=True)
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("InProgress", "In Progress"),
        ("Completed", "Completed"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, null=False, blank=False, default="Pending")
    priority = models.IntegerField(null=False, blank=False, default=0)
    leader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="led_tasks",
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="tasks",
        blank=True
    )
    parent_task = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    dependencies = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True
    )
    due_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, related_name="comments", on_delete=models.CASCADE)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="authored_comments",
        on_delete=models.CASCADE
    )
    create_date = models.DateTimeField(auto_now_add=True)
    content = models.CharField(max_length=300, null=False, blank=False)

    def __str__(self):
        return f"Comment by {self.author.username} on {self.task.title}"
