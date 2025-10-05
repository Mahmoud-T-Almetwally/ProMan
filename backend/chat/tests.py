import pytest
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from channels.testing import WebsocketCommunicator
from asgiref.sync import sync_to_async

from core.asgi import application # Your ASGI application
from projects.models import Project
from .models import Chat
from common.models import File

User = get_user_model()

@pytest.mark.django_db
@pytest.mark.asyncio
class ChatConsumerTests(TransactionTestCase):
    """
    Tests for the ChatConsumer.
    """
    async def asyncSetUp(self):
        """
        Set up the database with users, projects, and chats asynchronously.
        Note: We use asyncSetUp because the tests are async.
        """
        self.user1 = await sync_to_async(User.objects.create_user)(username='user1', email='user1@proman.com', password='password123')
        self.user2 = await sync_to_async(User.objects.create_user)(username='user2', email='user2@proman.com', password='password123')
        self.non_member = await sync_to_async(User.objects.create_user)(username='nonmember', email='nonmember@proman.com', password='password123')

        self.project1_chat = await sync_to_async(Chat.objects.create)()
        self.project1 = await sync_to_async(Project.objects.create)(
            owner=self.user1,
            title="Project 1",
            chat=self.project1_chat,
            finish_date="2026-01-01T00:00:00Z"
        )
        await sync_to_async(self.project1.members.add)(self.user2)

        self.project2_chat = await sync_to_async(Chat.objects.create)()
        self.project2 = await sync_to_async(Project.objects.create)(
            owner=self.user2,
            title="Project 2",
            chat=self.project2_chat,
            finish_date="2026-01-01T00:00:00Z"
        )

        self.file1 = await sync_to_async(File.objects.create)(
            name="testfile.txt",
            type="text/plain",
            size=100,
            uploader=self.user1
        )

    async def create_authenticated_communicator(self, user, chat_id):
        communicator = WebsocketCommunicator(application, f"/ws/chat/{chat_id}/")
        communicator.scope['user'] = user
        return communicator

    async def test_authenticated_project_member_can_connect(self):
        """
        Ensure a user who is part of the project can connect successfully.
        """
        await self.asyncSetUp()
        communicator = await self.create_authenticated_communicator(self.user1, self.project1_chat.id)
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_unauthenticated_user_is_rejected(self):
        """
        Ensure an anonymous user's connection is closed.
        """

        await self.asyncSetUp()
        
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.project1_chat.id}/")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)

    async def test_non_project_member_is_rejected(self):
        """
        Ensure a user who is not part of the project is rejected.
        """
        await self.asyncSetUp()
        communicator = await self.create_authenticated_communicator(self.non_member, self.project1_chat.id)
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_send_message_is_saved_and_broadcast(self):
        """
        Ensure a sent message is saved to the DB and broadcast to all members of the chat.
        """
        
        await self.asyncSetUp()
        
        comm1 = await self.create_authenticated_communicator(self.user1, self.project1_chat.id)
        await comm1.connect()
        
        comm2 = await self.create_authenticated_communicator(self.user2, self.project1_chat.id)
        await comm2.connect()

        await comm1.send_json_to({
            "type": "chat_message",
            "message": "Hello, world!"
        })

        response = await comm2.receive_json_from()
        self.assertEqual(response['type'], 'chat_message')
        self.assertEqual(response['message']['content'], 'Hello, world!')
        self.assertEqual(response['message']['sender']['username'], 'user1')

        response_sender = await comm1.receive_json_from()
        self.assertEqual(response_sender['message']['content'], 'Hello, world!')

        from chat.models import Message
        message_count = await sync_to_async(Message.objects.count)()
        self.assertEqual(message_count, 1)

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_send_message_with_attachment(self):
        """
        Ensure messages with file attachments are handled correctly.
        """
        await self.asyncSetUp()
        comm1 = await self.create_authenticated_communicator(self.user1, self.project1_chat.id)
        await comm1.connect()
        comm2 = await self.create_authenticated_communicator(self.user2, self.project1_chat.id)
        await comm2.connect()

        await comm1.send_json_to({
            "type": "chat_message",
            "message": "Check this file",
            "attached_files": [str(self.file1.id)]
        })

        response = await comm2.receive_json_from()
        self.assertEqual(len(response['message']['attached']), 1)
        self.assertEqual(response['message']['attached'][0]['id'], str(self.file1.id))
        self.assertEqual(response['message']['attached'][0]['name'], 'testfile.txt')

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_message_not_sent_to_different_chat(self):
        """
        Ensure a message sent in one chat is not broadcast to another chat.
        """

        await self.asyncSetUp()
        comm_project1 = await self.create_authenticated_communicator(self.user1, self.project1_chat.id)
        await comm_project1.connect()
        
        comm_project2 = await self.create_authenticated_communicator(self.user2, self.project2_chat.id)
        await comm_project2.connect()

        await comm_project1.send_json_to({
            "type": "chat_message",
            "message": "This is a private message for Project 1"
        })

        self.assertTrue(await comm_project2.receive_nothing())

        await comm_project1.disconnect()
        await comm_project2.disconnect()

    async def test_typing_indicator_is_broadcast(self):
        """
        Ensure typing indicators are broadcast correctly to other users in the room.
        """
        await self.asyncSetUp()
        comm1 = await self.create_authenticated_communicator(self.user1, self.project1_chat.id)
        await comm1.connect()
        comm2 = await self.create_authenticated_communicator(self.user2, self.project1_chat.id)
        await comm2.connect()

        await comm1.send_json_to({
            "type": "user_typing",
            "is_typing": True
        })

        response = await comm2.receive_json_from()
        self.assertEqual(response['type'], 'user_typing')
        self.assertEqual(response['user']['username'], 'user1')
        self.assertTrue(response['is_typing'])

        self.assertTrue(await comm1.receive_nothing())

        await comm1.disconnect()
        await comm2.disconnect()