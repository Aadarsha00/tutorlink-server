from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta
from .models import Application
from .serializers import ApplicationSerializer, ApplicationListSerializer
from notifications.services import NotificationService


class ApplicationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == "teacher":
            return (
                Application.objects.filter(teacher=user)
                .select_related("gig", "gig__parent")
                .order_by("-created_at")
            )
        elif user.role == "parent":
            return (
                Application.objects.filter(gig__parent=user)
                .select_related("teacher", "gig")
                .order_by("-created_at")
            )
        return Application.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationSerializer

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """Teacher accepts selection"""
        application = self.get_object()

        if application.teacher != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        if application.status != "selected":
            return Response(
                {"error": "Application is not in selected state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update application
        application.status = "accepted"
        application.responded_at = timezone.now()
        application.save()

        # Update gig
        gig = application.gig
        gig.hired_teacher = application.teacher
        gig.status = "payment_pending"
        gig.save()

        # Notify parent
        NotificationService.send_notification(
            user=gig.parent,
            notification_type="selection_accepted",
            title="Teacher Accepted!",
            message=f"{application.teacher.email} accepted your selection for {gig.title}",
            link=f"/parent/gigs/{gig.id}",
        )

        return Response({"status": "accepted"})

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Teacher rejects selection"""
        application = self.get_object()

        if application.teacher != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        if application.status != "selected":
            return Response(
                {"error": "Application is not in selected state"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update application
        application.status = "rejected"
        application.responded_at = timezone.now()
        application.save()

        # Update gig back to open/selection_pending
        gig = application.gig
        gig.selected_teacher = None
        gig.status = "open"
        gig.save()

        # Notify parent
        NotificationService.send_notification(
            user=gig.parent,
            notification_type="selection_rejected",
            title="Teacher Declined",
            message=f"{application.teacher.email} declined your selection for {gig.title}",
            link=f"/parent/gigs/{gig.id}/applications",
        )

        return Response({"status": "rejected"})

    @action(detail=True, methods=["post"])
    def select(self, request, pk=None):
        """Parent selects a teacher"""
        application = self.get_object()

        if application.gig.parent != request.user:
            return Response(
                {"error": "Not authorized"}, status=status.HTTP_403_FORBIDDEN
            )

        if application.status != "pending":
            return Response(
                {"error": "Application is not pending"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update application
        application.status = "selected"
        application.selected_at = timezone.now()
        application.response_deadline = timezone.now() + timedelta(days=2)
        application.save()

        # Update gig
        gig = application.gig
        gig.selected_teacher = application.teacher
        gig.status = "confirmation_pending"
        gig.save()

        # Notify teacher
        NotificationService.send_notification(
            user=application.teacher,
            notification_type="teacher_selected",
            title="You've Been Selected!",
            message=f"You were selected for {gig.title}. Please respond within 48 hours.",
            link=f"/teacher/applications/{application.id}",
            metadata={
                "gig_id": gig.id,
                "application_id": application.id,
                "response_deadline": application.response_deadline.isoformat(),
            },
        )

        return Response({"status": "selected"})
