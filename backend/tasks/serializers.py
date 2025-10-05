from rest_framework import serializers
from .models import Task, Comment
from users.serializers import UserListSerializer


class CommentSerializer(serializers.ModelSerializer):
    author = UserListSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'author', 'create_date', 'content')
        read_only_fields = ('author', 'create_date')


class TaskListSerializer(serializers.ModelSerializer):
    """A lightweight serializer for task list views."""
    leader = UserListSerializer(read_only=True)

    class Meta:
        model = Task
        fields = ('id', 'title', 'status', 'priority', 'due_date', 'leader')

class RecursiveTaskSerializer(serializers.Serializer):
    def to_representation(self, value):
        serializer = self.parent.parent.__class__(value, context=self.context)
        return serializer.data

class TaskDetailSerializer(serializers.ModelSerializer):
    """A detailed serializer for a single task."""
    leader = UserListSerializer(read_only=True)
    members = UserListSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    subtasks = RecursiveTaskSerializer(many=True, read_only=True)
    dependencies = TaskListSerializer(many=True, read_only=True)
    parent_task = TaskListSerializer(read_only=True)

    class Meta:
        model = Task
        fields = ('id', 'phase', 'title', 'description', 'status', 'priority', 
                  'leader', 'members', 'parent_task', 'subtasks', 'dependencies', 
                  'comments', 'due_date')

class TaskCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating tasks with validation."""
    
    class Meta:
        model = Task
        fields = ('title', 'description', 'status', 'priority', 
                  'leader', 'parent_task', 'due_date')

    def validate_parent_task(self, value):
        """
        Ensure a task is not set as its own parent.
        """
        if self.instance and self.instance.pk == value.pk:
            raise serializers.ValidationError("A task cannot be its own parent.")
        return value

    def validate(self, data):
        """
        Validate leader and due date against the parent phase/project.
        """

        if self.instance:
            phase = self.instance.phase
        else:
            phase = self.context.get('phase')

        if not phase:
            raise serializers.ValidationError("Phase context is missing for validation.")
         
        leader = data.get('leader')
        project = phase.project

        if leader and leader not in project.members.all() and \
           leader not in project.supervisors.all() and project.owner != leader:
            raise serializers.ValidationError("The task leader must be a member of the project.")

        due_date = data.get('due_date')
        if due_date and (due_date.date() > phase.end_date.date() or due_date.date() < phase.begin_date.date()):
            raise serializers.ValidationError("Task due date must be within the parent phase's dates.")
            
        return data
    
class TaskMemberUpdateSerializer(serializers.Serializer):
    """Serializer for adding/removing multiple users."""
    user_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )