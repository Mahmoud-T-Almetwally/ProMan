from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Task, Comment
from projects.models import Phase
from users.serializers import UserListSerializer 


User = get_user_model()


class CommentSerializer(serializers.ModelSerializer):
    """
    Serializer for creating, listing, and retrieving comments.
    When reading, it nests a summary of the author.
    When creating, the author is automatically set to the logged-in user in the view.
    """

    author = UserListSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = [
            'id',
            'author',
            'content',
            'create_date',
            'task'
        ]

        read_only_fields = ['id', 'author', 'create_date']
        extra_kwargs = {
            'task': {'write_only': True}
        }


class TaskParentSerializer(serializers.ModelSerializer):
    """
    A minimal serializer to represent a parent task.
    Used to prevent deep, recursive nesting in the TaskDetailSerializer.
    """
    class Meta:
        model = Task
        fields = ['id', 'title']


class TaskListSerializer(serializers.ModelSerializer):
    """
    A summarized serializer for LIST views (e.g., Kanban board cards).
    Provides just enough information to display a task "card" without over-fetching.
    """
    
    leader = UserListSerializer(read_only=True)
    
    comment_count = serializers.IntegerField(source='comments.count', read_only=True)
    member_count = serializers.IntegerField(source='members.count', read_only=True)
    subtask_count = serializers.IntegerField(source='subtasks.count', read_only=True)

    class Meta:
        model = Task
        fields = [
            'id',
            'title',
            'status',
            'priority',
            'due_date',
            'leader',
            'comment_count',
            'member_count',
            'subtask_count'
        ]


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    The full-detail serializer for RETRIEVE views.
    Nests all related objects like members, comments, subtasks, and dependencies
    to provide a complete picture of the task.
    """
    
    phase = serializers.PrimaryKeyRelatedField(read_only=True)
    leader = UserListSerializer(read_only=True)
    members = UserListSerializer(many=True, read_only=True)
    
    subtasks = TaskListSerializer(many=True, read_only=True)
    dependencies = TaskListSerializer(many=True, read_only=True)
    
    parent_task = TaskParentSerializer(read_only=True)
    
    comments = CommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Task
        fields = [
            'id',
            'title',
            'description',
            'status',
            'priority',
            'due_date',
            'phase',
            'leader',
            'members',
            'parent_task',
            'subtasks',
            'dependencies',
            'comments',
        ]


class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    """
    A versatile serializer for both CREATING and UPDATING tasks.
    It uses PrimaryKeyRelatedField for relationships, expecting IDs from the frontend
    for fields like 'leader', 'members', 'dependencies', etc.
    """
    
    members = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), 
        many=True,
        required=False
    )
    
    dependencies = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(),
        many=True,
        required=False
    )
    
    leader = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )
    
    phase = serializers.PrimaryKeyRelatedField(
        queryset=Phase.objects.all()
    )
    
    parent_task = serializers.PrimaryKeyRelatedField(
        queryset=Task.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Task
        fields = [
            'title',
            'description',
            'status',
            'priority',
            'due_date',
            'phase',
            'leader',
            'members',
            'parent_task',
            'dependencies',
        ]
        
    def validate(self, data):
        """
        Custom validation to prevent a task from being its own parent or dependency.
        """
        if self.instance:
            parent_task = data.get('parent_task')
            if parent_task and parent_task.id == self.instance.id:
                raise serializers.ValidationError("A task cannot be its own parent.")
            
            dependencies = data.get('dependencies', [])
            if self.instance in dependencies:
                raise serializers.ValidationError("A task cannot have itself as a dependency.")

        return data


class TaskStatusUpdateSerializer(serializers.ModelSerializer):
    """
    A highly specific and lightweight serializer for only updating a task's status.
    Use Case: Ideal for a drag-and-drop Kanban board where the only change is the
    status, making the API call fast and efficient.
    """
    class Meta:
        model = Task
        fields = ['status']