from rest_framework import permissions
from .models import Task


class IsProjectMemberForTask(permissions.BasePermission):
    """
    Allows read access if the user is a member of the task's parent project.
    """
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Task):
            return request.user in obj.phase.project.members.all() or \
                request.user in obj.phase.project.supervisors.all() or \
                obj.phase.project.owner == request.user
        return False 

class CanManageTask(permissions.BasePermission):
    """
    Allows write access if the user is the project owner, a supervisor, or the task leader.
    """
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Task):
            project = obj.phase.project
            return project.owner == request.user or \
                request.user in project.supervisors.all() or \
                obj.leader == request.user
        return False

class IsCommentAuthor(permissions.BasePermission):
    """
    Allows access only to the author of the comment.
    """
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user