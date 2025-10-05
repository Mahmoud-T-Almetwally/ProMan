from django.urls import path, include
from rest_framework_nested import routers
from .views import ProjectViewSet, PhaseViewSet


router = routers.SimpleRouter()
router.register(r'projects', ProjectViewSet, basename='project')

projects_router = routers.NestedSimpleRouter(router, r'projects', lookup='project')
projects_router.register(r'phases', PhaseViewSet, basename='project-phases')

urlpatterns = [
    path('', include(router.urls)),
    path('', include(projects_router.urls)),
]