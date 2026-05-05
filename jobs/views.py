from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from .models import Job, JobApplication
from .serializers import (
    AdminJobApplicationUpdateSerializer,
    JobApplicationListSerializer,
    JobApplicationSerializer,
    JobListSerializer,
    JobSerializer,
)


class JobViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    search_fields = ["title", "school_name", "subject", "grade", "location"]
    ordering_fields = ["created_at", "updated_at", "deadline", "salary_min", "salary_max"]

    def get_queryset(self):
        user = self.request.user

        if user.role == "admin":
            return Job.objects.all().order_by("-created_at")

        if user.role == "teacher":
            return (
                Job.objects.filter(
                    Q(status="open") | Q(applications__teacher=user)
                )
                .distinct()
                .order_by("-created_at")
            )

        return Job.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return JobListSerializer
        return JobSerializer

    def perform_create(self, serializer):
        published_at = timezone.now() if serializer.validated_data.get("status") == "open" else None
        serializer.save(created_by=self.request.user, published_at=published_at)

    def perform_update(self, serializer):
        old_status = serializer.instance.status
        job = serializer.save()

        updates = []
        if old_status != "open" and job.status == "open" and not job.published_at:
            job.published_at = timezone.now()
            updates.append("published_at")
        if old_status != job.status and job.status in ["closed", "cancelled"]:
            job.closed_at = timezone.now()
            updates.append("closed_at")
        if updates:
            job.save(update_fields=updates)

    def create(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response(
                {"error": "Only admins can create jobs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response(
                {"error": "Only admins can update jobs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response(
                {"error": "Only admins can update jobs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != "admin":
            return Response(
                {"error": "Only admins can delete jobs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["get"], permission_classes=[IsAuthenticated])
    def applications(self, request, pk=None):
        job = self.get_object()
        if request.user.role != "admin":
            return Response(
                {"error": "Only admins can view job applicants."},
                status=status.HTTP_403_FORBIDDEN,
            )

        applications = job.applications.select_related(
            "job", "teacher", "cv_document", "cv_document__teacher"
        ).order_by("-created_at")
        serializer = JobApplicationListSerializer(
            applications, many=True, context={"request": request}
        )
        return Response(serializer.data)


class JobApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = JobApplicationSerializer

    def get_queryset(self):
        user = self.request.user

        if user.role == "teacher":
            return JobApplication.objects.filter(teacher=user).select_related(
                "job", "teacher", "cv_document", "cv_document__teacher"
            )
        if user.role == "admin":
            return JobApplication.objects.all().select_related(
                "job", "teacher", "cv_document", "cv_document__teacher"
            )

        return JobApplication.objects.none()

    def get_serializer_class(self):
        if self.request.user.role == "admin" and self.action in [
            "update",
            "partial_update",
        ]:
            return AdminJobApplicationUpdateSerializer
        if self.action == "list":
            return JobApplicationListSerializer
        return JobApplicationSerializer

    def create(self, request, *args, **kwargs):
        if request.user.role != "teacher":
            return Response(
                {"error": "Only teachers can apply for jobs."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        application = self.get_object()
        if request.user.role != "admin" and application.teacher != request.user:
            return Response(
                {"error": "You can only delete your own job applications."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def withdraw(self, request, pk=None):
        application = self.get_object()

        if application.teacher != request.user:
            return Response(
                {"error": "You can only withdraw your own job applications."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if application.status not in ["pending", "reviewed", "shortlisted"]:
            return Response(
                {"error": "This job application can no longer be withdrawn."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.status = "withdrawn"
        application.save(update_fields=["status", "updated_at"])
        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)
