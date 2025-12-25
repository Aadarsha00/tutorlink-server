from django.db import transaction
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from accounts.models import User
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and sending notifications"""

    @classmethod
    @transaction.atomic
    def send_notification(
        cls,
        user: User,
        notification_type: str,
        title: str,
        message: str,
        link: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Notification:
        """
        Create a notification and send it via WebSocket

        Args:
            user: User to receive the notification
            notification_type: Type of notification (see Notification.TYPE_CHOICES)
            title: Notification title
            message: Notification message
            link: Optional link for the notification
            metadata: Optional additional data

        Returns:
            Created Notification instance
        """
        # Create notification in database
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            metadata=metadata or {},
        )

        # Send via WebSocket
        cls._send_to_websocket(notification)

        # Send email for critical notifications
        if cls._is_critical_notification(notification_type):
            cls._send_email_notification(notification)

        logger.info(f"Notification sent to user {user.id}: {notification_type}")

        return notification

    @classmethod
    def _send_to_websocket(cls, notification: Notification):
        """Send notification to user via WebSocket"""
        try:
            channel_layer = get_channel_layer()
            user_channel = f"user_{notification.user.id}"

            async_to_sync(channel_layer.group_send)(
                user_channel,
                {
                    "type": "notification.new",
                    "data": {
                        "id": notification.id,
                        "notification_type": notification.notification_type,
                        "title": notification.title,
                        "message": notification.message,
                        "link": notification.link,
                        "metadata": notification.metadata,
                        "created_at": notification.created_at.isoformat(),
                    },
                },
            )
        except Exception as e:
            logger.error(f"Failed to send WebSocket notification: {e}")

    @classmethod
    def _is_critical_notification(cls, notification_type: str) -> bool:
        """Determine if notification requires email"""
        critical_types = [
            "teacher_selected",
            "selection_accepted",
            "selection_rejected",
            "escrow_funded",
            "payment_released",
            "dispute_opened",
        ]
        return notification_type in critical_types

    @classmethod
    def _send_email_notification(cls, notification: Notification):
        """Send email notification (async via Celery)"""
        from .tasks import send_notification_email

        try:
            send_notification_email.delay(notification.id)
        except Exception as e:
            logger.error(f"Failed to queue email notification: {e}")

    @classmethod
    def mark_as_read(cls, notification_id: int, user: User) -> bool:
        """Mark a notification as read"""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()
            return True
        except Notification.DoesNotExist:
            return False

    @classmethod
    def mark_all_as_read(cls, user: User) -> int:
        """Mark all notifications as read for a user"""
        count = Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
        return count

    @classmethod
    def get_unread_count(cls, user: User) -> int:
        """Get count of unread notifications"""
        return Notification.objects.filter(user=user, is_read=False).count()

    @classmethod
    def delete_old_notifications(cls, days: int = 90):
        """Delete notifications older than specified days"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        count = Notification.objects.filter(
            created_at__lt=cutoff_date, is_read=True
        ).delete()[0]
        logger.info(f"Deleted {count} old notifications")
        return count


class ApplicationNotificationService:
    """Service for application-related notifications"""

    @classmethod
    def notify_application_received(cls, application):
        """Notify parent when teacher applies"""
        NotificationService.send_notification(
            user=application.gig.parent,
            notification_type="application_received",
            title="New Application Received",
            message=f"A teacher applied to your {application.gig.title} gig",
            link=f"/parent/gigs/{application.gig.id}/applications",
            metadata={
                "gig_id": application.gig.id,
                "application_id": application.id,
                "teacher_id": application.teacher.id,
            },
        )

    @classmethod
    def notify_teacher_selected(cls, application):
        """Notify teacher when selected by parent"""
        NotificationService.send_notification(
            user=application.teacher,
            notification_type="teacher_selected",
            title="You've Been Selected!",
            message=f"You were selected for {application.gig.title}. Please respond within 48 hours.",
            link=f"/teacher/applications/{application.id}",
            metadata={
                "gig_id": application.gig.id,
                "application_id": application.id,
                "response_deadline": (
                    application.response_deadline.isoformat()
                    if application.response_deadline
                    else None
                ),
            },
        )

    @classmethod
    def notify_selection_accepted(cls, application):
        """Notify parent when teacher accepts"""
        NotificationService.send_notification(
            user=application.gig.parent,
            notification_type="selection_accepted",
            title="Teacher Accepted!",
            message=f"Teacher accepted your selection for {application.gig.title}. Proceed to payment.",
            link=f"/parent/gigs/{application.gig.id}",
            metadata={
                "gig_id": application.gig.id,
                "application_id": application.id,
                "teacher_id": application.teacher.id,
            },
        )

    @classmethod
    def notify_selection_rejected(cls, application):
        """Notify parent when teacher rejects"""
        NotificationService.send_notification(
            user=application.gig.parent,
            notification_type="selection_rejected",
            title="Teacher Declined",
            message=f"Teacher declined your selection for {application.gig.title}. You can select another applicant.",
            link=f"/parent/gigs/{application.gig.id}/applications",
            metadata={"gig_id": application.gig.id, "application_id": application.id},
        )


class EscrowNotificationService:
    """Service for escrow-related notifications"""

    @classmethod
    def notify_payment_initiated(cls, escrow):
        """Notify when parent initiates payment"""
        # Notify teacher
        NotificationService.send_notification(
            user=escrow.teacher,
            notification_type="payment_initiated",
            title="Payment Initiated",
            message=f"Parent is processing payment for {escrow.gig.title}",
            link=f"/teacher/gigs/{escrow.gig.id}",
            metadata={"escrow_id": escrow.id, "gig_id": escrow.gig.id},
        )

    @classmethod
    def notify_escrow_funded(cls, escrow):
        """Notify when escrow is funded"""
        # Notify teacher
        NotificationService.send_notification(
            user=escrow.teacher,
            notification_type="escrow_funded",
            title="Payment Secured",
            message=f"Escrow funded for {escrow.gig.title}. You can start teaching!",
            link=f"/teacher/gigs/{escrow.gig.id}",
            metadata={
                "escrow_id": escrow.id,
                "gig_id": escrow.gig.id,
                "amount": float(escrow.teacher_amount),
            },
        )

        # Notify parent
        NotificationService.send_notification(
            user=escrow.parent,
            notification_type="gig_started",
            title="Tuition Started",
            message=f"{escrow.gig.title} is now active",
            link=f"/parent/gigs/{escrow.gig.id}",
            metadata={"escrow_id": escrow.id, "gig_id": escrow.gig.id},
        )

    @classmethod
    def notify_completion_requested(cls, escrow):
        """Notify admin when parent requests completion"""
        # Get all admin users
        admin_users = User.objects.filter(role="admin", is_active=True)

        for admin in admin_users:
            NotificationService.send_notification(
                user=admin,
                notification_type="completion_requested",
                title="Completion Request",
                message=f"Parent requested completion for {escrow.gig.title}",
                link=f"/admin/escrow/{escrow.id}",
                metadata={"escrow_id": escrow.id, "gig_id": escrow.gig.id},
            )

    @classmethod
    def notify_payment_released(cls, escrow):
        """Notify when payment is released"""
        # Notify teacher
        NotificationService.send_notification(
            user=escrow.teacher,
            notification_type="payment_released",
            title="Payment Released",
            message=f"You received Rs. {escrow.teacher_amount} for {escrow.gig.title}",
            link=f"/teacher/earnings",
            metadata={
                "escrow_id": escrow.id,
                "gig_id": escrow.gig.id,
                "amount": float(escrow.teacher_amount),
            },
        )

        # Notify parent
        NotificationService.send_notification(
            user=escrow.parent,
            notification_type="gig_completed",
            title="Gig Completed",
            message=f"{escrow.gig.title} has been completed successfully",
            link=f"/parent/gigs/{escrow.gig.id}",
            metadata={"escrow_id": escrow.id, "gig_id": escrow.gig.id},
        )

    @classmethod
    def notify_payment_refunded(cls, escrow):
        """Notify when payment is refunded"""
        NotificationService.send_notification(
            user=escrow.parent,
            notification_type="payment_refunded",
            title="Payment Refunded",
            message=f"Rs. {escrow.amount} refunded for {escrow.gig.title}",
            link=f"/parent/gigs/{escrow.gig.id}",
            metadata={
                "escrow_id": escrow.id,
                "gig_id": escrow.gig.id,
                "amount": float(escrow.amount),
            },
        )

    @classmethod
    def notify_dispute_opened(cls, escrow, opened_by: User, reason: str):
        """Notify all parties when dispute is opened"""
        # Notify the other party
        other_party = escrow.teacher if opened_by == escrow.parent else escrow.parent

        NotificationService.send_notification(
            user=other_party,
            notification_type="dispute_opened",
            title="Dispute Opened",
            message=f"A dispute was opened for {escrow.gig.title}",
            link=f"/disputes/{escrow.id}",
            metadata={
                "escrow_id": escrow.id,
                "gig_id": escrow.gig.id,
                "reason": reason,
            },
        )

        # Notify all admins
        admin_users = User.objects.filter(role="admin", is_active=True)
        for admin in admin_users:
            NotificationService.send_notification(
                user=admin,
                notification_type="dispute_opened",
                title="New Dispute",
                message=f"Dispute opened for {escrow.gig.title}",
                link=f"/admin/escrow/{escrow.id}",
                metadata={
                    "escrow_id": escrow.id,
                    "gig_id": escrow.gig.id,
                    "opened_by": opened_by.id,
                },
            )


class PremiumNotificationService:
    """Service for premium subscription notifications"""

    @classmethod
    def notify_premium_activated(cls, teacher: User, subscription):
        """Notify when premium is activated"""
        NotificationService.send_notification(
            user=teacher,
            notification_type="premium_activated",
            title="Premium Activated!",
            message=f'Your premium subscription is now active until {subscription.expires_at.strftime("%B %d, %Y")}',
            link="/teacher/premium",
            metadata={
                "subscription_id": subscription.id,
                "expires_at": subscription.expires_at.isoformat(),
            },
        )

    @classmethod
    def notify_premium_expiring(cls, teacher: User, subscription):
        """Notify when premium is about to expire"""
        NotificationService.send_notification(
            user=teacher,
            notification_type="premium_expiring",
            title="Premium Expiring Soon",
            message=f'Your premium subscription expires on {subscription.expires_at.strftime("%B %d, %Y")}',
            link="/teacher/premium",
            metadata={
                "subscription_id": subscription.id,
                "expires_at": subscription.expires_at.isoformat(),
            },
        )

    @classmethod
    def notify_premium_expired(cls, teacher: User):
        """Notify when premium has expired"""
        NotificationService.send_notification(
            user=teacher,
            notification_type="premium_expired",
            title="Premium Expired",
            message="Your premium subscription has expired. Renew to continue enjoying premium benefits.",
            link="/teacher/premium",
        )
