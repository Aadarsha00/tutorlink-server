from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import JobApplicationViewSet, JobViewSet

router = DefaultRouter()
router.register(r"jobs", JobViewSet, basename="job")
router.register(r"job-applications", JobApplicationViewSet, basename="job-application")

urlpatterns = [
    path("", include(router.urls)),
]
