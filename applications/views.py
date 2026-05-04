from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import Application
from .serializers import ApplicationSerializer, ApplicationListSerializer
from notifications.services import ApplicationNotificationService
import logging

logger = logging.getLogger(__name__)


class ApplicationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job applications
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        """
        Filter applications based on user role
        - Teachers see their own applications
        - Parents see applications to their gigs
        - Admins see all applications
        """
        user = self.request.user

        if user.role == "teacher":
            return Application.objects.filter(teacher=user).select_related(
                "gig", "teacher", "gig__parent"
            )
        elif user.role == "parent":
            return Application.objects.filter(gig__parent=user).select_related(
                "gig", "teacher"
            )
        elif user.role == "admin":
            return Application.objects.all().select_related("gig", "teacher")

        return Application.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return ApplicationListSerializer
        return ApplicationSerializer

    def perform_create(self, serializer):
        """
        Create application and send notification to parent
        """
        try:
            # Save the application
            application = serializer.save()

            logger.info(
                f"Application created: ID={application.id}, "
                f"Teacher={application.teacher.email}, "
                f"Gig={application.gig.title}"
            )

            # Send notification to parent
            try:
                ApplicationNotificationService.notify_application_received(application)
                logger.info(
                    f"✅ Notification sent to parent {application.gig.parent.email} "
                    f"for gig '{application.gig.title}'"
                )
            except Exception as e:
                logger.error(f"❌ Failed to send notification: {e}")
                # Don't fail the application creation if notification fails

        except Exception as e:
            logger.error(f"❌ Failed to create application: {e}")
            raise

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def withdraw(self, request, pk=None):
        """
        Withdraw an application (Teacher only)

        POST /applications/{id}/withdraw/
        """
        application = self.get_object()

        # Only the teacher who applied can withdraw
        if application.teacher != request.user:
            return Response(
                {"error": "You can only withdraw your own applications"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Can only withdraw pending applications
        if application.status != "pending":
            return Response(
                {"error": "Can only withdraw pending applications"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.status = "withdrawn"
        application.save()

        logger.info(
            f"Application {application.id} withdrawn by teacher {request.user.email}"
        )

        return Response(
            {"message": "Application withdrawn successfully"},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def select(self, request, pk=None):
        """
        Select an application (Parent only)
        Sets 48-hour response deadline for teacher

        POST /applications/{id}/select/
        """
        application = self.get_object()

        # Only the gig owner (parent) can select
        if application.gig.parent != request.user:
            return Response(
                {"error": "Only the gig owner can select applicants"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Can only select pending applications
        if application.status != "pending":
            return Response(
                {"error": "Can only select pending applications"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if gig is still open
        if application.gig.status != "open":
            return Response(
                {"error": "This gig is no longer accepting applications"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update application status
        application.status = "selected"
        application.selected_at = timezone.now()
        application.response_deadline = timezone.now() + timedelta(hours=48)
        application.save()

        # Update gig status
        application.gig.status = "selection_pending"
        application.gig.selected_teacher = application.teacher
        application.gig.save()

        logger.info(
            f"Application {application.id} selected by parent {request.user.email}. "
            f"Deadline: {application.response_deadline}"
        )

        # Send notification to teacher
        try:
            ApplicationNotificationService.notify_teacher_selected(application)
            logger.info(
                f"✅ Selection notification sent to teacher {application.teacher.email}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to send selection notification: {e}")

        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def accept(self, request, pk=None):
        """
        Accept a selection (Teacher only)
        Teacher accepts parent's selection within 48 hours

        POST /applications/{id}/accept/
        """
        application = self.get_object()

        # Only the selected teacher can accept
        if application.teacher != request.user:
            return Response(
                {"error": "You can only accept your own selections"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Can only accept selected applications
        if application.status != "selected":
            return Response(
                {"error": "Can only accept selected applications"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if deadline has passed
        if (
            application.response_deadline
            and timezone.now() > application.response_deadline
        ):
            return Response(
                {"error": "Response deadline has passed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update application
        application.status = "accepted"
        application.responded_at = timezone.now()
        application.save()

        # Update gig status
        application.gig.status = "payment_pending"
        application.gig.hired_teacher = application.teacher
        application.gig.save()

        # Reject all other pending/selected applications for this gig
        Application.objects.filter(
            gig=application.gig, status__in=["pending", "selected"]
        ).exclude(id=application.id).update(status="rejected")

        logger.info(
            f"Application {application.id} accepted by teacher {request.user.email}. "
            f"Gig moving to payment_pending."
        )

        # Send notification to parent
        try:
            ApplicationNotificationService.notify_selection_accepted(application)
            logger.info(
                f"✅ Acceptance notification sent to parent {application.gig.parent.email}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to send acceptance notification: {e}")

        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def reject(self, request, pk=None):
        """
        Reject a selection (Teacher only)
        Teacher declines parent's selection

        POST /applications/{id}/reject/
        """
        application = self.get_object()

        # Only the selected teacher can reject
        if application.teacher != request.user:
            return Response(
                {"error": "You can only reject your own selections"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Can only reject selected applications
        if application.status != "selected":
            return Response(
                {"error": "Can only reject selected applications"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update application
        application.status = "rejected"
        application.responded_at = timezone.now()
        application.save()

        # Revert gig status back to open
        application.gig.status = "open"
        application.gig.selected_teacher = None
        application.gig.save()

        logger.info(
            f"Application {application.id} rejected by teacher {request.user.email}. "
            f"Gig back to open status."
        )

        # Send notification to parent
        try:
            ApplicationNotificationService.notify_selection_rejected(application)
            logger.info(
                f"✅ Rejection notification sent to parent {application.gig.parent.email}"
            )
        except Exception as e:
            logger.error(f"❌ Failed to send rejection notification: {e}")

        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)
