from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Project, Phase
from common.models import File

User = get_user_model()

class ProjectViewSetTests(APITestCase):
    """
    Test suite for the ProjectViewSet.
    """
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email="owner@proman.com", password='pass123')
        self.supervisor = User.objects.create_user(username='supervisor', email="supervisor@proman.com", password='pass123')
        self.member = User.objects.create_user(username='member', email="member@proman.com", password='pass123')
        self.other_user = User.objects.create_user(username='other', email="other@proman.com", password='pass123')

        self.project = Project.objects.create(
            owner=self.owner,
            title="Test Project",
            description="A project for testing.",
            finish_date="2026-01-01T00:00:00Z",
            start_date="2026-02-01T00:00:00Z",
        )
        self.project.supervisors.add(self.supervisor)
        self.project.members.add(self.member)

        self.file = File.objects.create(name="test.txt", type="text/plain", size=100, uploader=self.owner)

    def test_unauthenticated_user_cannot_access_projects(self):
        """Ensure unauthenticated users get a 401 Unauthorized error."""
        response = self.client.get('/api/projects/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_member_cannot_list_or_view_project(self):
        """Ensure a user not part of a project cannot see it."""
        self.client.force_authenticate(user=self.other_user)
        
        list_response = self.client.get('/api/projects/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 0)
        
        detail_response = self.client.get(f'/api/projects/{self.project.pk}/')
        self.assertEqual(detail_response.status_code, status.HTTP_404_NOT_FOUND)

    def test_member_can_view_but_not_edit_project(self):
        """Ensure a regular member has read-only access."""
        self.client.force_authenticate(user=self.member)

        get_response = self.client.get(f'/api/projects/{self.project.pk}/')
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        patch_response = self.client.patch(f'/api/projects/{self.project.pk}/', {'title': 'New Title'})
        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)

        delete_response = self.client.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_supervisor_can_edit_but_not_delete_project(self):
        """Ensure a supervisor has edit access but cannot delete."""
        self.client.force_authenticate(user=self.supervisor)
        patch_response = self.client.patch(f'/api/projects/{self.project.pk}/', {'title': 'New Title'})
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        delete_response = self.client.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(delete_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_has_full_access(self):
        """Ensure the owner can edit and delete the project."""
        self.client.force_authenticate(user=self.owner)
        patch_response = self.client.patch(f'/api/projects/{self.project.pk}/', {'title': 'New Title'})
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        delete_response = self.client.delete(f'/api/projects/{self.project.pk}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_create_project(self):
        """Test successful project creation."""
        self.client.force_authenticate(user=self.owner)
        url = '/api/projects/'
        data = {
            "title": "Another Project",
            "description": "Details here.",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Project.objects.count(), 2)
        new_project = Project.objects.get(id=response.data['id'])
        self.assertEqual(new_project.owner, self.owner)
        self.assertIsNotNone(new_project.chat)

    def test_supervisor_can_add_and_remove_members(self):
        """Test the /members custom action by a supervisor."""
        self.client.force_authenticate(user=self.supervisor)
        url = f'/api/projects/{self.project.pk}/members/'

        add_data = {'user_ids': [self.other_user.pk]}
        add_response = self.client.post(url, add_data)

        self.assertEqual(add_response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        self.assertIn(self.other_user, self.project.members.all())

        remove_data = {'user_ids': [self.member.pk]}
        remove_response = self.client.delete(url, remove_data)

        self.assertEqual(remove_response.status_code, status.HTTP_200_OK)
        self.project.refresh_from_db()
        self.assertNotIn(self.member, self.project.members.all())

    def test_owner_can_add_supervisors(self):
        """Test the /supervisors custom action by the owner."""
        self.client.force_authenticate(user=self.owner)
        url = f'/api/projects/{self.project.pk}/supervisors/'
        data = {'user_ids': [self.member.pk]}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.project.refresh_from_db()
        self.assertIn(self.member, self.project.supervisors.all())

    def test_supervisor_cannot_add_supervisors(self):
        """Ensure a supervisor cannot manage other supervisors (permission test)."""
        self.client.force_authenticate(user=self.supervisor)
        url = f'/api/projects/{self.project.pk}/supervisors/'
        data = {'user_ids': [self.member.pk]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_can_attach_and_detach_files(self):
        """Test the /files custom action."""
        self.client.force_authenticate(user=self.supervisor)
        url = f'/api/projects/{self.project.pk}/files/'
        attach_data = {'file_ids': [self.file.pk]}
        attach_response = self.client.post(url, attach_data)
        self.assertEqual(attach_response.status_code, status.HTTP_200_OK)
        self.assertIn(self.file, self.project.attached_files.all())
        detach_response = self.client.delete(url, attach_data)
        self.assertEqual(detach_response.status_code, status.HTTP_200_OK)
        self.assertNotIn(self.file, self.project.attached_files.all())


class PhaseViewSetTests(APITestCase):
    """
    Test suite for the PhaseViewSet, focused on nested functionality.
    """
    def setUp(self):
        self.owner = User.objects.create_user(username='p_owner', email='p_owner@proman.com', password='pass123')
        self.supervisor = User.objects.create_user(username='p_supervisor', email='p_supervisor@proman.com', password='pass123')
        self.member = User.objects.create_user(username='p_member', email='p_member@proman.com', password='pass123')
        self.non_member = User.objects.create_user(username='p_non_member', email='p_non_member@proman.com', password='pass123')
        
        self.project = Project.objects.create(owner=self.owner, title="Phase Project")
        self.project.supervisors.add(self.supervisor)
        self.project.members.add(self.member)

        self.phase = Phase.objects.create(
            project=self.project, 
            title="Initial Phase", 
            begin_date="2025-11-01T00:00:00Z",
            end_date="2025-11-15T00:00:00Z"
        )
        self.base_url = f'/api/projects/{self.project.pk}/phases/'
    
    def test_project_member_can_list_phases(self):
        """Ensure a project member can read phase data."""
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], self.phase.title)

    def test_project_member_cannot_create_phase(self):
        """Ensure a regular member cannot create a phase."""
        self.client.force_authenticate(user=self.member)
        data = { "title": "Unauthorized Phase", "begin_date": "2025-12-01T00:00:00Z", "end_date": "2025-12-15T00:00:00Z" }
        response = self.client.post(self.base_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_project_member_cannot_access_phases(self):
        """Ensure an outside user gets a 404 for the project's phases."""
        self.client.force_authenticate(user=self.non_member)
        response = self.client.get(self.base_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_supervisor_can_create_and_delete_phase(self):
        """Ensure a supervisor can manage phases within their project."""
        self.client.force_authenticate(user=self.supervisor)
        data = { "title": "Phase Two", "begin_date": "2025-12-01T00:00:00Z", "end_date": "2025-12-15T00:00:00Z" }

        create_response = self.client.post(self.base_url, data)
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.project.phases.count(), 2)

        phase_id = create_response.data['id']
        delete_response = self.client.delete(f'{self.base_url}{phase_id}/')
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(self.project.phases.count(), 1)
    
    def test_cannot_add_non_project_member_to_phase(self):
        """
        CRITICAL TEST: Ensure a user who is not in the parent project
        cannot be added as a member to a phase within that project.
        """
        self.client.force_authenticate(user=self.owner)
        url = f'{self.base_url}{self.phase.pk}/members/'
        data = {'user_ids': [self.non_member.pk]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.phase.refresh_from_db()
        self.assertNotIn(self.non_member, self.phase.members.all())
        self.assertEqual(self.phase.members.count(), 0)

    def test_can_add_project_member_to_phase(self):
        """Test successfully adding an existing project member to a phase."""
        self.client.force_authenticate(user=self.owner)
        self.assertNotIn(self.member, self.phase.members.all())
        url = f'{self.base_url}{self.phase.pk}/members/'
        data = {'user_ids': [self.member.pk]}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.phase.refresh_from_db()
        self.assertIn(self.member, self.phase.members.all())