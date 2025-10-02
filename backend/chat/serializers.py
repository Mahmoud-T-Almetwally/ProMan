from rest_framework import serializers

from .models import Chat, Message

from common.models import File

from users.serializers import UserListSerializer
from common.serializers import FileSerializer


class MessageSerializer(serializers.ModelSerializer):
    """
    Serializer for listing messages and creating new ones.
    
    - For READ operations, it nests the sender's and attachments' details.
    - For WRITE operations, it validates the content and attachment IDs.
      The 'sender' and 'chat' are set programmatically in the view.
    """
    sender = UserListSerializer(read_only=True)
    attached = FileSerializer(many=True, read_only=True)

    attached_ids = serializers.PrimaryKeyRelatedField(
        queryset=File.objects.all(),
        source='attached',
        many=True,
        write_only=True,
        required=False
    )

    class Meta:
        model = Message
        fields = [
            'id',
            'sender',
            'content',
            'send_date',
            'attached',
            'attached_ids'
        ]
        read_only_fields = ['id', 'sender', 'send_date']

    def create(self, validated_data):
        """
        The 'sender' and 'chat' are not in validated_data because they are not
        part of the serializer's writable fields. They must be passed from the
        view into the serializer's save() method.
        
        Example from the view:
        serializer.save(sender=self.request.user, chat=self.get_chat_object())
        """
        return super().create(validated_data)


class ChatDetailSerializer(serializers.ModelSerializer):
    """
    A read-only serializer for retrieving a chat's history.
    It nests the list of messages, which will be paginated by the view
    to handle long conversations efficiently.
    """
    project_id = serializers.IntegerField(source='project.id', read_only=True)
    
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Chat
        fields = [
            'id',
            'project_id',
            'messages'
        ]