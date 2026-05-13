from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, InvalidOperation
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

        # Update gig status. Other pending applications stay pending so the parent
        # can select another teacher if this pre-payment match is cancelled.
        application.gig.status = "payment_pending"
        application.gig.hired_teacher = application.teacher
        application.gig.save()

        # Open messaging after both sides have accepted the match.
        try:
            from messaging.services import ConversationService

            ConversationService.get_or_create_for_gig(application.gig)
        except Exception as e:
            logger.error(f"Failed to create conversation for gig {application.gig.id}: {e}")

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
    def cancel_match(self, request, pk=None):
        """
        Cancel an accepted pre-payment match.

        POST /applications/{id}/cancel-match/
        """
        application = self.get_object()
        user = request.user
        reason = (request.data.get("reason") or "").strip()[:300]

        if user.id not in {application.gig.parent_id, application.teacher_id}:
            return Response(
                {"error": "Only the matched parent or teacher can cancel this match"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if application.status != "accepted":
            return Response(
                {"error": "Only accepted matches can be cancelled"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if application.gig.status != "payment_pending":
            return Response(
                {
                    "error": "Only pre-payment matches can be cancelled here. Active gigs require a cancellation or dispute flow."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            application.status = "cancelled"
            application.match_cancelled_at = timezone.now()
            application.match_cancelled_by = user
            application.match_cancel_reason = reason
            application.save(
                update_fields=[
                    "status",
                    "match_cancelled_at",
                    "match_cancelled_by",
                    "match_cancel_reason",
                    "updated_at",
                ]
            )

            gig = application.gig
            gig.status = "open"
            gig.selected_teacher = None
            gig.hired_teacher = None
            gig.save(update_fields=["status", "selected_teacher", "hired_teacher", "updated_at"])

            try:
                from messaging.services import ConversationService

                ConversationService.close_for_gig(gig)
            except Exception as e:
                logger.error(f"Failed to close conversation for gig {gig.id}: {e}")

        try:
            ApplicationNotificationService.notify_match_cancelled(
                application, cancelled_by=user, reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to send match cancellation notification: {e}")

        logger.info(
            f"Application {application.id} match cancelled by {user.email}. "
            f"Gig {application.gig.id} reopened."
        )

        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _minimum_rate_for_gig(self, gig):
        monthly_sessions = Decimal(max(gig.sessions_per_week, 1) * 4)
        return (Decimal("5000") / monthly_sessions).quantize(Decimal("0.01"))

    def _validate_rate_change(self, application, user):
        if user.id not in {application.gig.parent_id, application.teacher_id}:
            return Response(
                {"error": "Only the matched parent or teacher can change this rate"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if application.status != "accepted" or application.gig.status != "payment_pending":
            return Response(
                {"error": "Rate can only be changed before payment is completed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return None

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def propose_rate(self, request, pk=None):
        """
        Propose a rate change before parent payment.

        POST /applications/{id}/propose-rate/
        """
        application = self.get_object()
        validation_error = self._validate_rate_change(application, request.user)
        if validation_error:
            return validation_error

        try:
            new_rate = Decimal(str(request.data.get("proposed_rate", "")))
        except (InvalidOperation, TypeError):
            return Response(
                {"error": "Enter a valid per-session rate"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        minimum_rate = self._minimum_rate_for_gig(application.gig)
        monthly_total = new_rate * Decimal(application.gig.sessions_per_week) * Decimal("4")

        if new_rate <= 0:
            return Response(
                {"error": "Per-session rate must be greater than zero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if monthly_total < Decimal("5000"):
            return Response(
                {
                    "error": (
                        f"Minimum monthly fare is Rs. 5000. For "
                        f"{application.gig.sessions_per_week} sessions/week, "
                        f"minimum rate is Rs. {minimum_rate}/session."
                    ),
                    "minimum_rate": str(minimum_rate),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        application.rate_change_proposed_rate = new_rate
        application.rate_change_proposed_by = request.user
        application.rate_change_proposed_at = timezone.now()
        application.save(
            update_fields=[
                "rate_change_proposed_rate",
                "rate_change_proposed_by",
                "rate_change_proposed_at",
                "updated_at",
            ]
        )

        try:
            ApplicationNotificationService.notify_rate_change_requested(application)
        except Exception as e:
            logger.error(f"Failed to send rate proposal notification: {e}")

        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def respond_rate(self, request, pk=None):
        """
        Approve or reject a pending rate change.

        POST /applications/{id}/respond-rate/
        """
        application = self.get_object()
        validation_error = self._validate_rate_change(application, request.user)
        if validation_error:
            return validation_error

        if not application.rate_change_proposed_rate:
            return Response(
                {"error": "There is no pending rate proposal"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if application.rate_change_proposed_by_id == request.user.id:
            return Response(
                {"error": "The other party must respond to this rate proposal"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        decision = request.data.get("decision")
        proposed_rate = application.rate_change_proposed_rate

        if decision == "approve":
            old_rate = application.proposed_rate

            with transaction.atomic():
                application.proposed_rate = proposed_rate
                application.rate_change_proposed_rate = None
                application.rate_change_proposed_by = None
                application.rate_change_proposed_at = None
                application.save(
                    update_fields=[
                        "proposed_rate",
                        "rate_change_proposed_rate",
                        "rate_change_proposed_by",
                        "rate_change_proposed_at",
                        "updated_at",
                    ]
                )

                try:
                    from payments.models import GigPayment

                    platform_fee = (
                        proposed_rate
                        * Decimal("0.10")
                        * Decimal("4")
                        * Decimal(application.gig.sessions_per_week)
                    )
                    GigPayment.objects.filter(gig=application.gig).exclude(
                        status="completed"
                    ).update(amount=platform_fee, platform_fee=platform_fee)
                except Exception as e:
                    logger.error(f"Failed to sync approved payment amount: {e}")

            try:
                ApplicationNotificationService.notify_rate_change_approved(
                    application, approved_by=request.user, old_rate=old_rate
                )
            except Exception as e:
                logger.error(f"Failed to send rate approval notification: {e}")

        elif decision == "reject":
            application.rate_change_proposed_rate = None
            application.rate_change_proposed_by = None
            application.rate_change_proposed_at = None
            application.save(
                update_fields=[
                    "rate_change_proposed_rate",
                    "rate_change_proposed_by",
                    "rate_change_proposed_at",
                    "updated_at",
                ]
            )

            try:
                ApplicationNotificationService.notify_rate_change_rejected(
                    application, rejected_by=request.user, rejected_rate=proposed_rate
                )
            except Exception as e:
                logger.error(f"Failed to send rate rejection notification: {e}")

        else:
            return Response(
                {"error": "Decision must be approve or reject"},
                status=status.HTTP_400_BAD_REQUEST,
            )

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
