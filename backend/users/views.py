from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, generics, mixins
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action

from rest_framework_simplejwt.tokens import RefreshToken

from .models import Notification
from .serializers import (
    UserCreateSerializer,
    UserListSerializer,
    UserDetailSerializer,
    NotificationSerializer,
    NotificationUpdateSerializer,
)

User = get_user_model()


class UserRegisterView(generics.CreateAPIView):
    """
    Endpoint for user registration.
    Accessible by: Anyone
    """
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserCreateSerializer


class LogoutView(generics.GenericAPIView):
    """
    Endpoint for user logout. Blacklists the refresh token.
    Accessible by: Authenticated Users
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(mixins.ListModelMixin,
                  mixins.RetrieveModelMixin,
                  mixins.UpdateModelMixin,
                  viewsets.GenericViewSet):
    """
    A ViewSet for listing, retrieving, and updating users.
    - list:   GET /api/user/
    - retrieve: GET /api/user/{pk}/
    - A custom /profile endpoint for the authenticated user to manage their own profile.
    
    Accessible by: Authenticated Users
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        return UserDetailSerializer 

    @action(detail=False, methods=['get', 'put', 'patch'], url_path='profile')
    def me(self, request, *args, **kwargs):
        """
        An endpoint for the authenticated user to view and edit their own profile.
        """
        self.kwargs['pk'] = request.user.pk
        
        if request.method == 'GET':
            return self.retrieve(request, *args, **kwargs)
        elif request.method == 'PUT':
            return self.update(request, *args, **kwargs)
        elif request.method == 'PATCH':
            return self.partial_update(request, *args, **kwargs)


class NotificationViewSet(viewsets.ModelViewSet):
    """
    A ViewSet for the authenticated user to manage their notifications.
    Accessible by: Authenticated Users
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        This is the crucial security step: ensure users can only access
        their own notifications.
        """
        return Notification.objects.filter(recipient=self.request.user).order_by('-create_date')

    def get_serializer_class(self):
        """
        Use the lightweight serializer for updates to prevent users from
        changing notification content.
        """
        if self.action in ['update', 'partial_update']:
            return NotificationUpdateSerializer
        return NotificationSerializer

    @action(detail=False, methods=['post'], url_path='mark-all-as-read')
    def mark_all_as_read(self, request, *args, **kwargs):
        """
        A custom action to mark all of the user's unread notifications as read.
        """
        unread_notifications = self.get_queryset().filter(is_read=False)
        
        unread_notifications.update(is_read=True)
        
        return Response(status=status.HTTP_204_NO_CONTENT)