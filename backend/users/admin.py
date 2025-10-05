from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Import the models from the current app
from .models import Notification

# Get the custom User model
User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom User Admin to display and manage the custom fields.
    We inherit from the base UserAdmin to keep all the default functionality
    like password management, permissions, etc.
    """
    
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'profile_image' 
    )

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Custom Profile Information', {
            'fields': ('profile_image',)
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Custom Profile Information', {
            'fields': ('profile_image',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin view for the Notification model.
    Provides filtering, searching, and a clear list display for easy management.
    """
    list_display = (
        'recipient',
        'content',
        'is_read',
        'create_date',
    )

    list_filter = (
        'is_read',
        'recipient',
    )

    search_fields = (
        'content',
        'recipient__username',
    )

    readonly_fields = (
        'create_date',
    )

    ordering = ('-create_date',)