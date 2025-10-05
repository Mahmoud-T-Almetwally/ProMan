import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async

from .models import Message
from projects.models import Project
from common.models import File
from users.serializers import UserListSerializer
from common.serializers import FileSerializer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat_group_name = f'chat_{self.chat_id}'
        self.user = self.scope['user']
        
        if not self.user.is_authenticated:
            await self.close()
            return

        is_member = await self.is_project_member()
        if not is_member:
            await self.close()
            return

        await self.channel_layer.group_add(
            self.chat_group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.chat_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type')

        if event_type == 'chat_message':
            await self.handle_chat_message(data)
        elif event_type == 'user_typing':
            await self.handle_user_typing(data)

    async def handle_chat_message(self, event):
        message_content = event.get('message', '')
        attached_file_ids = event.get('attached_files', [])

        new_message = await self.create_db_message(message_content, attached_file_ids)
        
        message_data = {
            'id': str(new_message.id),
            'chat': str(new_message.chat.id),
            'sender': UserListSerializer(new_message.sender).data,
            'send_date': new_message.send_date.isoformat(),
            'content': new_message.content,
            'attached': FileSerializer(new_message.attached.all(), many=True).data
        }
        
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'broadcast_chat_message',
                'message': message_data
            }
        )
    
    async def handle_user_typing(self, event):
        await self.channel_layer.group_send(
            self.chat_group_name,
            {
                'type': 'broadcast_user_typing',
                'user': UserListSerializer(self.user).data,
                'is_typing': event.get('is_typing', False)
            }
        )

    async def broadcast_chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message']
        }))

    async def broadcast_user_typing(self, event):
        if str(self.user.id) != event['user']['id']:
            await self.send(text_data=json.dumps({
                'type': 'user_typing',
                'user': event['user'],
                'is_typing': event['is_typing']
            }))

    @sync_to_async
    def is_project_member(self):
        try:
            project = Project.objects.get(chat__id=self.chat_id)
            return (project.owner == self.user or
                    self.user in project.supervisors.all() or
                    self.user in project.members.all())
        except Project.DoesNotExist:
            return False

    @sync_to_async
    def create_db_message(self, content, file_ids):
        message = Message.objects.create(
            chat_id=self.chat_id,
            sender=self.user,
            content=content
        )
        if file_ids:
            files = File.objects.filter(id__in=file_ids)
            message.attached.set(files)
        
        return Message.objects.select_related('sender', 'chat').prefetch_related('attached').get(id=message.id)