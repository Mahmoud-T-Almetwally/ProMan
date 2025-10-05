from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import Project, Phase
from .permissions import IsProjectOwner, IsProjectOwnerOrSupervisor, IsProjectMember
from .serializers import (
    ProjectListSerializer,
    ProjectDetailSerializer,
    ProjectCreateUpdateSerializer,
    ProjectMemberUpdateSerializer,
    AttachedFilesUpdateSerializer,
    PhaseSerializer,
)

from chat.models import Chat
from common.models import File

User = get_user_model()


class ProjectViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for creating, viewing, and editing projects.
    """
    queryset = Project.objects.all()

    def get_queryset(self):
        """
        This view should return a list of all the projects
        for the currently authenticated user.
        """
        user = self.request.user
        
        return Project.objects.filter(
            Q(owner=user) | Q(supervisors=user) | Q(members=user)
        ).distinct()

    def get_serializer_class(self):
        """
        Return different serializers for different actions.
        """
        if self.action == 'list':
            return ProjectListSerializer
        if self.action in ['create', 'update', 'partial_update']:
            return ProjectCreateUpdateSerializer
        return ProjectDetailSerializer

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        - `IsProjectMember` for retrieve (read).
        - `IsProjectOwnerOrSupervisor` for updates.
        - `IsProjectOwner` for destroy.
        - `IsAuthenticated` for list/create.
        """

        if self.action == 'retrieve':
            self.permission_classes = [IsAuthenticated, IsProjectMember]
        elif self.action in ['update', 'partial_update', 'members', 'files']:
            self.permission_classes = [IsAuthenticated, IsProjectOwnerOrSupervisor]
        elif self.action in ['supervisors', 'destroy']:
            self.permission_classes = [IsAuthenticated, IsProjectOwner]
        else:
            self.permission_classes = [IsAuthenticated]
            
        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Automatically set the owner and create a chat when a new project is created.
        """
        user = self.request.user
        chat = Chat.objects.create()
        serializer.save(owner=user, chat=chat)

    @action(detail=True, methods=['post', 'delete'])
    def members(self, request, pk=None):
        """
        Custom action to add or remove members from a project.
        """
        project = self.get_object()
        serializer = ProjectMemberUpdateSerializer(data=request.data)
        if serializer.is_valid():
            user_ids = serializer.validated_data['user_ids']
            users = User.objects.filter(id__in=user_ids)

            if request.method == 'POST':
                project.members.add(*users)
                return Response({'status': 'Members added successfully.'}, status=status.HTTP_200_OK)
            
            elif request.method == 'DELETE':
                project.members.remove(*users)
                return Response({'status': 'Members removed successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'])
    def supervisors(self, request, pk=None):
        """
        Custom action to add or remove supervisors. Only the owner can perform this.
        """
        project = self.get_object()
        serializer = ProjectMemberUpdateSerializer(data=request.data)
        if serializer.is_valid():
            user_ids = serializer.validated_data['user_ids']
            users = User.objects.filter(id__in=user_ids)

            if request.method == 'POST':
                project.supervisors.add(*users)
                return Response({'status': 'Supervisors added successfully.'}, status=status.HTTP_200_OK)
            
            elif request.method == 'DELETE':
                project.supervisors.remove(*users)
                return Response({'status': 'Supervisors removed successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post', 'delete'])
    def files(self, request, pk=None):
        """
        Custom action to attach or detach files from a project.
        """
        project = self.get_object()
        serializer = AttachedFilesUpdateSerializer(data=request.data)
        if serializer.is_valid():
            file_ids = serializer.validated_data['file_ids']
            files = File.objects.filter(id__in=file_ids)

            if request.method == 'POST':
                project.attached_files.add(*files)
                return Response({'status': 'Files attached successfully.'}, status=status.HTTP_200_OK)

            elif request.method == 'DELETE':
                project.attached_files.remove(*files)
                return Response({'status': 'Files detached successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PhaseViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for creating, viewing, and editing phases within a project.
    Accessed via `/api/projects/{project_pk}/phases/`
    """
    serializer_class = PhaseSerializer

    def get_project(self):
        """Helper method to get the parent project and check permissions."""
        project_pk = self.kwargs['project_pk']
        project = get_object_or_404(Project, pk=project_pk)
        self.check_object_permissions(self.request, project)
        return project

    def get_queryset(self):
        """
        Filter phases to only return those belonging to the specified project.
        """
        project = self.get_project()
        return Phase.objects.filter(project=project)

    def get_permissions(self):
        """
        Permissions are based on the membership of the parent project.
        - Members can read.
        - Owners/Supervisors can write.
        """
        
        if self.action in ['list', 'retrieve']:
            self.permission_classes = [IsAuthenticated, IsProjectMember]
        else:
            self.permission_classes = [IsAuthenticated, IsProjectOwnerOrSupervisor]

        return super().get_permissions()

    def perform_create(self, serializer):
        """
        Automatically associate the phase with the project from the URL.
        """
        project = self.get_project()
        serializer.save(project=project)

    @action(detail=True, methods=['post', 'delete'], url_path='members')
    def manage_members(self, request, pk=None, project_pk=None):
        """
        Custom action to add or remove members from a phase.
        Ensures that a user can only be added to a phase if they are
        already a member of the parent project.
        """
        phase = self.get_object()
        project = phase.project
        serializer = ProjectMemberUpdateSerializer(data=request.data)

        if serializer.is_valid():
            user_ids = serializer.validated_data['user_ids']
            
            valid_users = project.members.filter(id__in=user_ids)
            
            if request.method == 'POST':
                phase.members.add(*valid_users)
                return Response({'status': f'{valid_users.count()} members added to phase.'}, status=status.HTTP_200_OK)

            elif request.method == 'DELETE':
                phase.members.remove(*valid_users)
                return Response({'status': f'{valid_users.count()} members removed from phase.'}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)