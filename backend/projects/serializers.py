from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Project, Phase

from users.serializers import UserListSerializer
from tasks.serializers import TaskListSerializer

User = get_user_model()


from common.serializers import FileSerializer


class PhaseDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for a Phase, designed to be NESTED inside a Project.
    It includes a list of all its tasks, using the summarized TaskListSerializer.
    This is the core of the hierarchical view.
    """
    
    tasks = TaskListSerializer(many=True, read_only=True)

    class Meta:
        model = Phase
        fields = [
            'id',
            'title',
            'description',
            'status',
            'picked_color',
            'begin_date',
            'end_date',
            'tasks',
        ]


class PhaseCreateUpdateSerializer(serializers.ModelSerializer):
    """
    A simple serializer for CREATING and UPDATING a Phase.
    It expects the project ID to associate itself.
    """
    project = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        write_only=True
    )

    class Meta:
        model = Phase
        fields = [
            'title',
            'description',
            'status',
            'picked_color',
            'begin_date',
            'end_date',
            'project',
        ]


class ProjectListSerializer(serializers.ModelSerializer):
    """
    Summarized project serializer for LIST views (e.g., a user's dashboard).
    Provides a high-level overview of the project without excessive detail.
    """
    owner = UserListSerializer(read_only=True)
    member_count = serializers.IntegerField(source='members.count', read_only=True)
    
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'description',
            'finish_date',
            'owner',
            'member_count',
            'task_count',
        ]

    def get_task_count(self, project):
        return project.phases.prefetch_related('tasks').values_list('tasks').count()


class ProjectDetailSerializer(serializers.ModelSerializer):
    """
    The full-detail serializer for a single Project.
    This is the primary serializer for viewing a project board, as it nests
    the phases, which in turn nest the tasks.
    """
    owner = UserListSerializer(read_only=True)
    supervisors = UserListSerializer(many=True, read_only=True)
    members = UserListSerializer(many=True, read_only=True)
    
    phases = PhaseDetailSerializer(many=True, read_only=True)
    
    chat = serializers.PrimaryKeyRelatedField(read_only=True)

    attached_files = FileSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'title',
            'description',
            'create_date',
            'finish_date',
            'owner',
            'supervisors',
            'members',
            'chat',
            'attached_files',
            'phases',
        ]


class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING and UPDATING a Project.
    Uses PrimaryKeyRelatedFields to handle assigning users. The owner is set
    automatically in the view.
    """
    owner = UserListSerializer(read_only=True)
    
    supervisors = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False
    )
    members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = Project
        fields = [
            'title',
            'description',
            'finish_date',
            'owner',
      'supervisors',
            'members',
        ]

    def create(self, validated_data):
        """
        Custom create logic to handle creating an associated Chat object.
        """
        
        from chat.models import Chat

        supervisors_data = validated_data.pop('supervisors', [])
        members_data = validated_data.pop('members', [])

        chat = Chat.objects.create()

        project = Project.objects.create(chat=chat, **validated_data)

        project.supervisors.set(supervisors_data)
        project.members.set(members_data)

        return project