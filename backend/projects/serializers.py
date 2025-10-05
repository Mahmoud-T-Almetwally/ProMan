from rest_framework import serializers
from .models import Project, Phase
from users.serializers import UserListSerializer
from common.serializers import FileSerializer


class PhaseSerializer(serializers.ModelSerializer):
    members = UserListSerializer(many=True, read_only=True)
    
    class Meta:
        model = Phase
        fields = ('id', 'title', 'description', 'status', 'picked_color', 
                  'begin_date', 'end_date', 'members')


class ProjectListSerializer(serializers.ModelSerializer):
    """A lightweight serializer for project list views."""
    owner = UserListSerializer(read_only=True)
    
    class Meta:
        model = Project
        fields = ('id', 'title', 'description', 'create_date', 'finish_date', 'start_date', 'owner')


class ProjectDetailSerializer(serializers.ModelSerializer):
    """A detailed serializer for a single project instance."""
    owner = UserListSerializer(read_only=True)
    supervisors = UserListSerializer(many=True, read_only=True)
    members = UserListSerializer(many=True, read_only=True)
    attached_files = FileSerializer(many=True, read_only=True)
    phases = PhaseSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = ('id', 'title', 'description', 'owner', 'supervisors', 
                  'members', 'phases', 'chat', 'attached_files', 
                  'create_date', 'finish_date', 'start_date')
        read_only_fields = ('owner', 'chat', 'create_date')


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer used for creating and updating projects."""
    class Meta:
        model = Project
        fields = ('id', 'title', 'description', 'finish_date', 'start_date')


class ProjectMemberUpdateSerializer(serializers.Serializer):
    """Serializer for adding/removing multiple users."""
    user_ids = serializers.ListField(
        child=serializers.UUIDField()
    )

class AttachedFilesUpdateSerializer(serializers.Serializer):
    """Serializer for adding/removing multiple files."""
    file_ids = serializers.ListField(
        child=serializers.UUIDField()
    )