from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TaskListCreateView,
    TaskViewSet,
    CommentListCreateView,
    CommentRetrieveUpdateDestroyView,
    MyTasksViewSet
)


router = DefaultRouter()
router.register(r'tasks', TaskViewSet, basename='task')

me_router = DefaultRouter()
me_router.register(r'me/tasks', MyTasksViewSet, basename='my-tasks')


urlpatterns = [
    # Manually defined URLs
    path('phases/<uuid:phase_id>/tasks/', TaskListCreateView.as_view(), name='phase-tasks'),
    path('tasks/<uuid:task_id>/comments/', CommentListCreateView.as_view(), name='task-comments-list'),
    path('tasks/<uuid:task_id>/comments/<uuid:pk>/', CommentRetrieveUpdateDestroyView.as_view(), name='task-comments-detail'),
    
    path('', include(router.urls)),
    path('', include(me_router.urls)),
]