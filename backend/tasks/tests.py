import datetime
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from projects.models import Project, Phase
from users.models import Notification
from .models import Task, Comment

User = get_user_model()


class TaskAPITests(APITestCase):
    """
    Comprehensive tests for the entire tasks API, including permissions,
    actions, and notification generation.
    """
    def setUp(self):
        
        self.owner = User.objects.create_user("owner", "owner@test.com", "password")
        self.supervisor = User.objects.create_user("supervisor", "sup@test.com", "password")
        self.member1 = User.objects.create_user("member1", "mem1@test.com", "password")
        self.member2 = User.objects.create_user("member2", "mem2@test.com", "password")
        self.outsider = User.objects.create_user("outsider", "out@test.com", "password")

        self.project = Project.objects.create(
            owner=self.owner,
            title="Test Project",
            finish_date=timezone.now() + datetime.timedelta(days=30)
        )
        self.project.supervisors.add(self.supervisor)
        self.project.members.add(self.member1, self.member2, self.supervisor)

        self.phase = Phase.objects.create(
            project=self.project,
            title="Test Phase",
            begin_date=timezone.now(),
            end_date=timezone.now() + datetime.timedelta(days=15)
        )

        self.task1 = Task.objects.create(
            phase=self.phase,
            title="Task 1",
            leader=self.member1,
            due_date=timezone.now() + datetime.timedelta(days=10)
        )
        self.task1.members.add(self.member2)

        self.task2 = Task.objects.create(
            phase=self.phase,
            title="Task 2 Led by Owner",
            leader=self.owner
        )
        self.task2.members.add(self.member1)

        self.comment = Comment.objects.create(
            task=self.task1,
            author=self.member2,
            content="This is a test comment."
        )

    def test_supervisor_can_create_task_and_notifications_are_sent(self):
        """
        Ensure a supervisor can create a task and notifications are sent to the owner and new leader.
        """
        self.client.force_authenticate(user=self.supervisor)
        url = f'/api/phases/{self.phase.id}/tasks/'
        data = {
            "title": "New Task by Supervisor",
            "leader": self.member2.id,
            "due_date": timezone.now() + datetime.timedelta(days=5)
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Notification.objects.filter(recipient=self.owner, content__contains="New Task by Supervisor").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.member2, content__contains="assigned as the leader").exists())
        self.assertFalse(Notification.objects.filter(recipient=self.supervisor).exists())

    def test_regular_member_cannot_create_task(self):
        """
        Ensure a user who is only a member (not owner/supervisor) cannot create a task.
        """
        self.client.force_authenticate(user=self.member1)
        url = f'/api/phases/{self.phase.id}/tasks/'
        data = {"title": "Should Fail"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_member_can_list_tasks_in_phase(self):
        """
        Ensure any project member can list the tasks for a specific phase.
        """
        self.client.force_authenticate(user=self.member2)
        url = f'/api/phases/{self.phase.id}/tasks/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_task_leader_can_update_task_and_status_change_sends_notification(self):
        """
        Ensure the task leader can update a task and a status change triggers notifications.
        """
        self.client.force_authenticate(user=self.member1)
        url = f'/api/tasks/{self.task1.id}/'
        data = {"status": "InProgress"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'InProgress')

        self.assertTrue(Notification.objects.filter(recipient=self.owner, content__contains="status of task 'Task 1' has been changed").exists())
        
        self.assertTrue(Notification.objects.filter(recipient=self.member2, content__contains="status of task 'Task 1' has been changed").exists())
        
        self.assertFalse(Notification.objects.filter(recipient=self.member1).exists())

    def test_regular_member_cannot_update_task(self):
        """
        Ensure a project member who is not a leader/owner/supervisor cannot update a task.
        """
        self.client.force_authenticate(user=self.member2)
        url = f'/api/tasks/{self.task2.id}/'
        data = {"status": "Completed"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_task_and_notification_is_sent(self):
        """
        Ensure the project owner can delete a task and relevant parties are notified.
        """
        self.client.force_authenticate(user=self.owner)
        url = f'/api/tasks/{self.task1.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        self.assertTrue(Notification.objects.filter(recipient=self.supervisor, content__contains="has been deleted").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.member1, content__contains="has been deleted").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.member2, content__contains="has been deleted").exists())
        
        self.assertFalse(Notification.objects.filter(recipient=self.owner).exists())

    def test_supervisor_can_add_member_to_task(self):
        """
        Ensure a supervisor can add a project member to a task and the member is notified.
        """
        self.client.force_authenticate(user=self.supervisor)

        url = f'/api/tasks/{self.task1.id}/members/'
        data = {"user_ids": [self.supervisor.id]}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertTrue(Notification.objects.filter(recipient=self.supervisor, content__contains="You have been added to the task").exists())

    def test_cannot_add_non_project_member_to_task(self):
        """
        Ensure an outsider cannot be added to a task.
        """
        self.client.force_authenticate(user=self.owner)
        url = f'/api/tasks/{self.task1.id}/members/'
        data = {"user_ids": [self.outsider.id]}
        response = self.client.post(url, data, format='json')
        
        self.task1.refresh_from_db()
        self.assertNotIn(self.outsider, self.task1.members.all())

    def test_project_member_can_post_comment_and_notifications_are_sent(self):
        """
        Ensure any project member can comment on a task, notifying the leader and other members.
        """
        self.client.force_authenticate(user=self.supervisor)
        url = f'/api/tasks/{self.task1.id}/comments/'
        data = {"content": "This is a new comment from the supervisor."}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertTrue(Notification.objects.filter(recipient=self.member1, content__contains="new comment was posted").exists())
        self.assertTrue(Notification.objects.filter(recipient=self.member2, content__contains="new comment was posted").exists())
        self.assertFalse(Notification.objects.filter(recipient=self.supervisor).exists())

    def test_comment_author_can_delete_own_comment(self):
        """
        Ensure a user can delete their own comment.
        """
        self.client.force_authenticate(user=self.member2)
        url = f'/api/tasks/{self.task1.id}/comments/{self.comment.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_user_cannot_delete_another_users_comment(self):
        """
        Ensure a user, even the project owner, cannot delete a comment made by another user.
        """
        self.client.force_authenticate(user=self.owner)
        url = f'/api/tasks/{self.task1.id}/comments/{self.comment.id}/'
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_my_tasks_endpoint_returns_all_assigned_tasks(self):
        """
        Test that /api/me/tasks/ returns tasks where the user is a leader or member, without duplicates.
        """
        
        self.client.force_authenticate(user=self.member1)
        url = '/api/me/tasks/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        task_titles = {task['title'] for task in response.data}
        self.assertIn('Task 1', task_titles)
        self.assertIn('Task 2 Led by Owner', task_titles)

    def test_my_tasks_led_endpoint(self):
        """
        Test that /api/me/tasks/led/ returns only tasks led by the user.
        """
        self.client.force_authenticate(user=self.member1)
        url = '/api/me/tasks/led/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Task 1')

    def test_my_tasks_member_endpoint(self):
        """
        Test that /api/me/tasks/member/ returns only tasks where the user is a member.
        """
        self.client.force_authenticate(user=self.member1)
        url = '/api/me/tasks/member/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Task 2 Led by Owner')