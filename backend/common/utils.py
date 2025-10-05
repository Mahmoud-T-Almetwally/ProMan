from users.models import Notification, User
from django.db.models import Q

def notify_users(recipients, message, exclude_user=None):
    """
    Creates a notification for a list or queryset of users.

    :param recipients: A list or queryset of User objects.
    :param message: The string content of the notification.
    :param exclude_user: (Optional) A User object to exclude from the notification list.
    """
    
    user_set = {user for user in recipients if user is not None}
    
    if exclude_user in user_set:
        user_set.remove(exclude_user)

    if not user_set:
        return

    notifications_to_create = [
        Notification(recipient=user, content=message)
        for user in user_set
    ]
    Notification.objects.bulk_create(notifications_to_create)