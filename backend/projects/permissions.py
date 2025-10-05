from rest_framework import permissions
from .models import Phase

class IsProjectOwner(permissions.BasePermission):
    """Allows access only to the project owner."""
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user

class IsProjectOwnerOrSupervisor(permissions.BasePermission):
    """Allows access to project owners or supervisors."""
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Phase):
            obj = obj.project
        return obj.owner == request.user or request.user in obj.supervisors.all()

class IsProjectMember(permissions.BasePermission):
    """Allows read access to any project member (owner, supervisor, or member)."""
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, Phase):
            obj = obj.project
        return (obj.owner == request.user or 
                request.user in obj.supervisors.all() or 
                request.user in obj.members.all())