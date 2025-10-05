from rest_framework import viewsets, status, generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import viewsets
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import Task, Comment
from .serializers import (
    TaskDetailSerializer, TaskListSerializer, TaskCreateUpdateSerializer,
    CommentSerializer, TaskMemberUpdateSerializer
)
from .permissions import IsProjectMemberForTask, CanManageTask, IsCommentAuthor
from projects.models import Phase
from projects.permissions import IsProjectMember, IsProjectOwnerOrSupervisor
from common.utils import notify_users

import logging

logger = logging.getLogger(__name__)


class TaskListCreateView(generics.ListCreateAPIView):
    """
    Endpoint to list tasks for a phase or create a new task within a phase.
    URL: /api/phases/{phase_id}/tasks/
    """
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TaskCreateUpdateSerializer
        return TaskListSerializer
    
    def get_serializer_context(self):
        """
        Pass the phase object to the serializer for validation during creation.
        """
        context = super().get_serializer_context()
        phase = get_object_or_404(Phase, pk=self.kwargs.get('phase_id'))
        context['phase'] = phase
        return context

    def get_queryset(self):
        phase_id = self.kwargs.get('phase_id')
        return Task.objects.filter(phase_id=phase_id).select_related('leader')

    def check_permissions(self, request):
        super().check_permissions(request)
        phase = get_object_or_404(Phase, pk=self.kwargs.get('phase_id'))
        project = phase.project
        
        if request.method == 'POST':
            if not IsProjectOwnerOrSupervisor().has_object_permission(request, self, project):
                self.permission_denied(request)
        else:
            if not IsProjectMember().has_object_permission(request, self, project):
                self.permission_denied(request)

    def perform_create(self, serializer):
        phase = self.get_serializer_context()['phase']
        project = phase.project
        task = serializer.save(phase=phase)

        recipients = list(project.supervisors.all()) + [project.owner]
        message = f"A new task '{task.title}' was created in project '{project.title}'."
        notify_users(recipients, message, exclude_user=self.request.user)

        if task.leader:
            leader_message = f"You have been assigned as the leader of a new task: '{task.title}'."
            notify_users([task.leader], leader_message, exclude_user=self.request.user)


class MyTasksViewSet(viewsets.ReadOnlyModelViewSet):
    """
    A ViewSet for the authenticated user to view tasks they are assigned to.
    Provides a list of all tasks where the user is a leader or a member.
    
    Endpoints:
    - GET /api/me/tasks/ : All tasks the user is assigned to.
    - GET /api/me/tasks/led/ : Tasks the user is leading.
    - GET /api/me/tasks/member/ : Tasks the user is a member of.
    """
    serializer_class = TaskListSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This view returns a list of all tasks for the currently authenticated user,
        including tasks they lead and tasks they are a member of.
        """
        user = self.request.user
        return Task.objects.filter(
            Q(leader=user) | Q(members=user)
        ).distinct().select_related('leader').order_by('due_date')

    @action(detail=False, methods=['get'])
    def led(self, request):
        """
        A convenience endpoint to retrieve only the tasks led by the current user.
        """
        user = request.user
        led_tasks = Task.objects.filter(leader=user).select_related('leader').order_by('due_date')
        
        page = self.paginate_queryset(led_tasks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = self.get_serializer(led_tasks, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def member(self, request):
        """
        A convenience endpoint to retrieve only the tasks where the current user is a member.
        """
        user = request.user
        member_tasks = Task.objects.filter(members=user).select_related('leader').order_by('due_date')

        page = self.paginate_queryset(member_tasks)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(member_tasks, many=True)
        return Response(serializer.data)


class TaskViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for retrieving, updating, deleting, and managing a single task's relationships.
    URL Namespace: /api/tasks/
    """
    queryset = Task.objects.all().prefetch_related('members', 'dependencies', 'subtasks').select_related('leader', 'parent_task', 'phase__project')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return TaskCreateUpdateSerializer
        return TaskDetailSerializer
    
    def get_permissions(self):
        """Instantiates and returns the list of permissions that this view requires."""
        if self.action in ['update', 'partial_update', 'destroy', 'members', 'dependencies']:
            self.permission_classes = [CanManageTask]
        else:
            self.permission_classes = [IsProjectMemberForTask]
        return super().get_permissions()

    def perform_update(self, serializer):
        original_task = self.get_object()
        original_leader = original_task.leader
        original_status = original_task.status

        updated_task = serializer.save()

        project = updated_task.phase.project
        recipients = list(updated_task.members.all()) + [updated_task.leader, project.owner]

        if updated_task.status != original_status:
            message = f"The status of task '{updated_task.title}' has been changed to '{updated_task.get_status_display()}'."
            notify_users(recipients, message, exclude_user=self.request.user)

        if updated_task.leader != original_leader:
            if original_leader:
                old_leader_msg = f"You are no longer the leader of task '{updated_task.title}'."
                notify_users([original_leader], old_leader_msg)
            if updated_task.leader:
                new_leader_msg = f"You have been assigned as the new leader of task '{updated_task.title}'."
                notify_users([updated_task.leader], new_leader_msg)

    def perform_destroy(self, instance):
        project = instance.phase.project
        recipients = list(instance.members.all()) + [instance.leader, project.owner] + list(project.supervisors.all())
        message = f"The task '{instance.title}' in project '{project.title}' has been deleted."
        
        instance.delete()
        
        notify_users(recipients, message, exclude_user=self.request.user)

    @action(detail=True, methods=['post', 'delete'], serializer_class=TaskMemberUpdateSerializer)
    def members(self, request, pk=None):
        """Add or remove members from a task."""
        task = self.get_object()
        project = task.phase.project
        serializer = TaskMemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_ids = serializer.validated_data['user_ids']
        
        potential_members = project.members.filter(id__in=user_ids)
        
        if request.method == 'POST':
            
            current_member_ids = set(task.members.values_list('id', flat=True))
            if task.leader:
                current_member_ids.add(task.leader.id)
            
            users_to_add = [user for user in potential_members if user.id not in current_member_ids]

            if not users_to_add:
                return Response({"status": "No new members to add."}, status=status.HTTP_200_OK)

            task.members.add(*users_to_add)
            message = f"You have been added to the task: '{task.title}'."
            notify_users(users_to_add, message)
            return Response({"status": "Members added successfully."}, status=status.HTTP_200_OK)
        
        elif request.method == 'DELETE':
            
            users_to_remove = project.members.filter(id__in=user_ids)
            task.members.remove(*users_to_remove)
            message = f"You have been removed from the task: '{task.title}'."
            notify_users(users_to_remove, message)
            return Response({"status": "Members removed successfully."}, status=status.HTTP_200_OK)


class CommentListCreateView(generics.ListCreateAPIView):
    """
    Endpoint to list all comments for a task or post a new one.
    URL: /api/tasks/{task_id}/comments/
    """
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Comment.objects.filter(task_id=self.kwargs.get('task_id')).order_by('create_date')

    def check_permissions(self, request):
        super().check_permissions(request)
        task = get_object_or_404(Task, pk=self.kwargs.get('task_id'))
        if not IsProjectMemberForTask().has_object_permission(request, self, task):
            self.permission_denied(request)

    def perform_create(self, serializer):
        task = get_object_or_404(Task, pk=self.kwargs.get('task_id'))
        comment = serializer.save(author=self.request.user, task=task)

        recipients = list(task.members.all()) + [task.leader]
        message = f"A new comment was posted on task '{task.title}' by {self.request.user.username}."
        notify_users(recipients, message, exclude_user=self.request.user)


class CommentRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    Endpoint to view, update, or delete a single comment.
    URL: /api/tasks/{task_id}/comments/{pk}/
    """
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'

    def get_queryset(self):
        return Comment.objects.filter(task_id=self.kwargs.get('task_id'))
    
    def get_permissions(self):
        """Set permissions based on the request method."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsCommentAuthor()]
        
        task = get_object_or_404(Task, pk=self.kwargs.get('task_id'))
        if not IsProjectMemberForTask().has_object_permission(self.request, self, task):
            self.permission_denied(self.request)
        return super().get_permissions()