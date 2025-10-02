from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Notification


User = get_user_model()


class UserListSerializer(serializers.ModelSerializer):
    """
    Summarized user serializer for LIST views.
    Use Case: Displaying lists of users (e.g., project members) where you only
    need essential, non-sensitive information.
    """
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 
            'username',
            'profile_image_url'
        ]
    
    def get_profile_image_url(self, user):
        """
        Return the full URL for the profile image, or None if it doesn't exist.
        """
        request = self.context.get('request')
        if user.profile_image and user.profile_image.file:
            return request.build_absolute_uri(user.profile_image.file.url)
        return None


class UserDetailSerializer(serializers.ModelSerializer):
    """
    Detailed user serializer for RETRIEVE views.
    Use Case: Viewing a specific user's profile (e.g., a user viewing their own
    profile). Exposes more information, like the email address.
    """
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'profile_image_url'
        ]
        read_only_fields = ['id']

    def get_profile_image_url(self, user):
        request = self.context.get('request')
        if user.profile_image and user.profile_image.file:
            return request.build_absolute_uri(user.profile_image.file.url)
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for CREATING new users (Registration).
    Use Case: User registration endpoint. This is the only place we should handle
    the password.
    """
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'first_name',
            'last_name',
        ]

    def create(self, validated_data):
        """
        Override the default create method to handle password hashing.
        """
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'] 
        )
        return user


class NotificationSerializer(serializers.ModelSerializer):
    """
    General-purpose serializer for listing and retrieving notifications.
    Use Case: Displaying a list of notifications for the currently logged-in user.
    """
    class Meta:
        model = Notification
        fields = [
            'id',
            'content',
            'is_read',
            'create_date'
        ]
        read_only_fields = ['id', 'content', "is_read", 'create_date']


class NotificationUpdateSerializer(serializers.ModelSerializer):
    """
    A specific, lightweight serializer for UPDATING a notification.
    Use Case: When a user marks a notification as read. This prevents them
    from accidentally (or maliciously) changing any other field, like the content.
    """
    class Meta:
        model = Notification
        fields = ['is_read']