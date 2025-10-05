from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Notification

User = get_user_model()


class UserRegistrationTests(APITestCase):
    """
    Tests for the UserRegisterView endpoint.
    """
    def test_user_can_register_successfully(self):
        """
        Ensure a new user can be created successfully with valid data.
        """
        url = '/api/auth/register/'
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "strongpassword123",
            "password2": "strongpassword123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, 'testuser')
        self.assertNotIn('password', response.data)

    def test_registration_fails_with_mismatched_passwords(self):
        """
        Ensure registration fails if the two password fields do not match.
        """
        url = '/api/auth/register/'
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User", 
            "password": "strongpassword123",
            "password2": "differentpassword"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)

    def test_registration_fails_with_existing_username(self):
        """
        Ensure registration fails if the username is already taken.
        """
        User.objects.create_user(username='testuser', password='password')
        url = '/api/auth/register/'
        data = {
            "username": "testuser",
            "email": "test@example.com",
            "password": "strongpassword123",
            "password2": "strongpassword123"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)


class AuthenticationTests(APITestCase):
    """
    Tests for user login (token generation) and logout.
    """
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email="user@proman.com", password='password123')

    def test_user_can_login_with_valid_credentials(self):
        """
        Ensure a user can obtain JWT tokens with a correct username and password.
        """
        url = '/api/auth/login/'
        data = {"username": "testuser", "password": "password123"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_user_login_fails_with_invalid_credentials(self):
        """
        Ensure token generation fails with an incorrect password.
        """
        url = '/api/auth/login/'
        data = {"username": "testuser", "password": "wrongpassword"}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_logout(self):
        """
        Ensure a user can logout by blacklisting their refresh token.
        """

        login_url = '/api/auth/login/'
        login_data = {"username": "testuser", "password": "password123"}
        login_response = self.client.post(login_url, login_data, format='json')
        refresh_token = login_response.data['refresh']

        logout_url = '/api/auth/logout/'
        logout_data = {"refresh": refresh_token}
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {login_response.data["access"]}')
        logout_response = self.client.post(logout_url, logout_data, format='json')
        
        self.assertEqual(logout_response.status_code, status.HTTP_205_RESET_CONTENT)

        refresh_url = '/api/auth/token/refresh/'
        refresh_data = {"refresh": refresh_token}
        refresh_response = self.client.post(refresh_url, refresh_data, format='json')
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)


class UserViewSetTests(APITestCase):
    """
    Tests for the UserViewSet, including the custom /profile endpoint.
    This test class demonstrates the correct way to test JWT-protected endpoints.
    """
    def setUp(self):
        
        self.user1 = User.objects.create_user(username='user1', email="user1@proman.com", password='password123', first_name='First1')
        self.user2 = User.objects.create_user(username='user2', email="user2@proman.com", password='password123')

        login_url = '/api/auth/login/'
        login_data = {'username': 'user1', 'password': 'password123'}
        response = self.client.post(login_url, login_data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def test_authenticated_user_can_list_users(self):
        """
        Ensure an authenticated user can retrieve the list of all users.
        """
        url = '/api/users/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn('username', response.data[0])
        self.assertNotIn('email', response.data[0])

    def test_unauthenticated_user_cannot_list_users(self):
        """
        Ensure unauthenticated users get a 401 Unauthorized error.
        """
        
        self.client.credentials() 
        
        url = '/api/users/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_user_can_retrieve_a_user(self):
        """
        Ensure a user can retrieve the detailed profile of another user.
        """
        url = f'/api/users/{self.user2.pk}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('email', response.data)
        self.assertEqual(response.data['username'], 'user2')
    
    
    def test_can_retrieve_own_profile_at_me_endpoint(self):
        """
        Ensure GET /api/users/profile/ returns the authenticated user's profile.
        """
        url = '/api/users/profile/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.user1.username)
        self.assertEqual(response.data['first_name'], 'First1')
    
    def test_can_update_own_profile_with_patch(self):
        """
        Ensure PATCH /api/users/profile/ updates the user's profile.
        """
        url = '/api/users/profile/'
        data = {"first_name": "UpdatedName"}
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, "UpdatedName")
        self.assertEqual(response.data['first_name'], "UpdatedName")


class NotificationViewSetTests(APITestCase):
    """
    Tests for the NotificationViewSet.
    Ensures that users can only access and manage their own notifications.
    """
    def setUp(self):
        self.user1 = User.objects.create_user(
            username='user1', 
            password='password123',
            email='user1@example.com'
        )
        self.user2 = User.objects.create_user(
            username='user2', 
            password='password123',
            email='user2@example.com'
        )
        
        self.notification1_user1 = Notification.objects.create(recipient=self.user1, content="Notification 1 for user 1", is_read=False)
        self.notification2_user1 = Notification.objects.create(recipient=self.user1, content="Notification 2 for user 1", is_read=True)
        self.notification1_user2 = Notification.objects.create(recipient=self.user2, content="Notification for user 2")

        login_url = '/api/auth/login/'
        login_data = {'username': 'user1', 'password': 'password123'}
        response = self.client.post(login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_token = response.data['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

    def test_unauthenticated_user_cannot_list_notifications(self):
        """
        Ensure unauthenticated users get a 401 Unauthorized error.
        """
        
        self.client.credentials()
        url = '/api/notifications/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_only_list_their_own_notifications(self):
        """
        Ensure the list endpoint only returns notifications for the authenticated user (user1).
        """
        url = '/api/notifications/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertEqual(len(response.data), 2)
        
        notification_contents = {item['content'] for item in response.data}
        self.assertIn(self.notification1_user1.content, notification_contents)
        self.assertIn(self.notification2_user1.content, notification_contents)
        self.assertNotIn(self.notification1_user2.content, notification_contents)

    def test_user_cannot_retrieve_another_users_notification(self):
        """
        Ensure a user gets a 404 when trying to access another user's notification by its ID.
        (The queryset filter makes it so the notification is not found for user1).
        """
        url = f'/api/notifications/{self.notification1_user2.id}/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_can_mark_their_notification_as_read(self):
        """
        Ensure a user can update their own notification (e.g., mark as read).
        """
        self.assertFalse(self.notification1_user1.is_read)
        
        url = f'/api/notifications/{self.notification1_user1.id}/'
        data = {"is_read": True}
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification1_user1.refresh_from_db()
        self.assertTrue(self.notification1_user1.is_read)

    def test_user_cannot_change_notification_content(self):
        """
        Ensure a user cannot change the content of a notification via a PATCH request,
        thanks to the NotificationUpdateSerializer.
        """
        url = f'/api/notifications/{self.notification1_user1.id}/'
        data = {"content": "maliciously changed content"}
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification1_user1.refresh_from_db()
        self.assertNotEqual(self.notification1_user1.content, data["content"])

    def test_mark_all_as_read_action(self):
        """
        Ensure the custom action marks all unread notifications as read for the authenticated user.
        """
        
        self.assertEqual(Notification.objects.filter(recipient=self.user1, is_read=False).count(), 1)
        
        url = '/api/notifications/mark-all-as-read/'
        response = self.client.post(url, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        self.assertEqual(Notification.objects.filter(recipient=self.user1, is_read=False).count(), 0)
        
        self.notification1_user2.refresh_from_db()
        self.assertFalse(self.notification1_user2.is_read)