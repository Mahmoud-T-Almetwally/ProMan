from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    UserRegisterView,
    LogoutView,
    UserViewSet,
    NotificationViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('auth/register/', UserRegisterView.as_view(), name='user_register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='user_logout'),
    
    path('', include(router.urls)),
]