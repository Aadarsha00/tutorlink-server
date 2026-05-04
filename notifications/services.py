# notifications/services.py - COMPLETE REWRITE for universal support

from django.db import transaction
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Notification
from accounts.models import User
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Universal service for creating and sending notifications to ALL users"""

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
        Works for ALL user roles: parent, teacher, admin

        Args:
            user: User to receive the notification (ANY ROLE)
            notification_type: Type of notification
            title: Notification title
            message: Notification message
            link: Optional link for the notification
            metadata: Optional additional data

        Returns:
            Created Notification instance
        """
        logger.info(
            f"📤 Creating notification for user {user.id} ({user.email}, {user.role}): {notification_type}"
        )

        # Create notification in database
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            metadata=metadata or {},
        )

        logger.info(
            f"✅ Notification created in DB: ID={notification.id} for user {user.id}"
        )

        # Send via WebSocket to ALL users regardless of role
        cls._send_to_websocket(notification)

        # Send email for critical notifications (ALL roles)
        if cls._is_critical_notification(notification_type):
            cls._send_email_notification(notification)

        logger.info(f"🎯 Notification fully processed for {user.role} user {user.id}")

        return notification

    @classmethod
    def send_bulk_notifications(
        cls,
        users: List[User],
        notification_type: str,
        title: str,
        message: str,
        link: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Notification]:
        """
        Send notifications to multiple users at once
        Useful for admin broadcasts or team notifications
        """
        notifications = []

        for user in users:
            try:
                notification = cls.send_notification(
                    user=user,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    link=link,
                    metadata=metadata,
                )
                notifications.append(notification)
            except Exception as e:
                logger.error(f"Failed to send notification to user {user.id}: {e}")

        logger.info(f"📨 Sent {len(notifications)} bulk notifications")
        return notifications

    @classmethod
    def _send_to_websocket(cls, notification: Notification):
        """Send notification to user via WebSocket - WORKS FOR ALL ROLES"""
        try:
            channel_layer = get_channel_layer()

            if not channel_layer:
                logger.warning("⚠️ Channel layer not configured - WebSocket disabled")
                return

            user_channel = f"user_{notification.user.id}"

            logger.info(
                f"🔔 Sending WebSocket to channel: {user_channel} (Role: {notification.user.role})"
            )

            # Send to user's channel
            async_to_sync(channel_layer.group_send)(
                user_channel,
                {
                    "type": "notification.new",
                    "data": {
                        "id": notification.id,
                        "user": notification.user.id,
                        "notification_type": notification.notification_type,
                        "title": notification.title,
                        "message": notification.message,
                        "link": notification.link,
                        "metadata": notification.metadata,
                        "is_read": notification.is_read,
                        "created_at": notification.created_at.isoformat(),
                    },
                },
            )

            logger.info(
                f"✅ WebSocket sent successfully to {notification.user.role} user {notification.user.id}"
            )

        except Exception as e:
            logger.error(
                f"❌ Failed to send WebSocket notification to user {notification.user.id}: {e}"
            )
            logger.exception("Full traceback:")

    @classmethod
    def _is_critical_notification(cls, notification_type: str) -> bool:
        """Determine if notification requires email - ROLE AGNOSTIC"""
        critical_types = [
            # Application critical
            "teacher_selected",
            "selection_accepted",
            "selection_rejected",
            # Disputes (for all parties)
            "dispute_opened",
            "dispute_resolved",
            # Admin critical
            "completion_requested",
            # Premium (teacher)
            "premium_expired",
        ]
        return notification_type in critical_types

    @classmethod
    def _send_email_notification(cls, notification: Notification):
        """Send email notification (async via Celery) - ALL ROLES"""
        try:
            from .tasks import send_notification_email

            send_notification_email.delay(notification.id)
            logger.info(f"📧 Email queued for user {notification.user.id}")
        except Exception as e:
            logger.error(f"Failed to queue email notification: {e}")

    @classmethod
    def mark_as_read(cls, notification_id: int, user: User) -> bool:
        """Mark a notification as read - WORKS FOR ALL ROLES"""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)

            if notification.is_read:
                logger.debug(f"Notification {notification_id} already read")
                return True

            notification.is_read = True
            notification.read_at = timezone.now()
            notification.save()

            logger.info(
                f"✓ Marked notification {notification_id} as read for {user.role} user {user.id}"
            )
            return True

        except Notification.DoesNotExist:
            logger.warning(
                f"❌ Notification {notification_id} not found for user {user.id}"
            )
            return False

    @classmethod
    def mark_all_as_read(cls, user: User) -> int:
        """Mark all notifications as read for a user - WORKS FOR ALL ROLES"""
        count = Notification.objects.filter(user=user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )

        logger.info(
            f"✓ Marked {count} notifications as read for {user.role} user {user.id}"
        )
        return count

    @classmethod
    def get_unread_count(cls, user: User) -> int:
        """Get count of unread notifications - WORKS FOR ALL ROLES"""
        count = Notification.objects.filter(user=user, is_read=False).count()
        logger.debug(f"Unread count for {user.role} user {user.id}: {count}")
        return count

    @classmethod
    def delete_old_notifications(cls, days: int = 90):
        """Delete notifications older than specified days - ALL USERS"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        count = Notification.objects.filter(
            created_at__lt=cutoff_date, is_read=True
        ).delete()[0]
        logger.info(f"Deleted {count} old notifications")
        return count


# ========================================
# ROLE-SPECIFIC NOTIFICATION SERVICES
# ========================================


class ApplicationNotificationService:
    """Application-related notifications - TEACHER & PARENT"""

    @classmethod
    def notify_application_received(cls, application):
        """Notify PARENT when teacher applies"""
        NotificationService.send_notification(
            user=application.gig.parent,
            notification_type="application_received",
            title="New Application Received",
            message=f"A teacher applied to your {application.gig.title} gig",
            link=f"/parent/gigs/{application.gig.id}",
            metadata={
                "gig_id": application.gig.id,
                "application_id": application.id,
                "teacher_id": application.teacher.id,
            },
        )

    @classmethod
    def notify_teacher_selected(cls, application):
        """Notify TEACHER when selected by parent"""
        NotificationService.send_notification(
            user=application.teacher,
            notification_type="teacher_selected",
            title="You've Been Selected!",
            message=f"You were selected for {application.gig.title}. Please respond within 48 hours.",
            link=f"/teacher/applications/",
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
        """Notify PARENT when teacher accepts"""
        NotificationService.send_notification(
            user=application.gig.parent,
            notification_type="selection_accepted",
            title="Teacher Accepted!",
            message=f"Teacher accepted your selection for {application.gig.title}. Proceed to payment.",
            link=f"/gigs/{application.gig.id}",
            metadata={
                "gig_id": application.gig.id,
                "application_id": application.id,
                "teacher_id": application.teacher.id,
            },
        )

    @classmethod
    def notify_selection_rejected(cls, application):
        """Notify PARENT when teacher rejects"""
        NotificationService.send_notification(
            user=application.gig.parent,
            notification_type="selection_rejected",
            title="Teacher Declined",
            message=f"Teacher declined your selection for {application.gig.title}. You can select another applicant.",
            link=f"/gigs/{application.gig.id}",
            metadata={"gig_id": application.gig.id, "application_id": application.id},
        )


class PremiumNotificationService:
    """Premium subscription notifications - TEACHER ONLY"""

    @classmethod
    def notify_premium_activated(cls, teacher: User, subscription):
        """Notify TEACHER when premium is activated"""
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
        """Notify TEACHER when premium is about to expire"""
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
        """Notify TEACHER when premium has expired"""
        NotificationService.send_notification(
            user=teacher,
            notification_type="premium_expired",
            title="Premium Expired",
            message="Your premium subscription has expired. Renew to continue enjoying premium benefits.",
            link="/teacher/premium",
        )


class SystemNotificationService:
    """System-wide notifications - ALL ROLES"""

    @classmethod
    def notify_all_users(cls, title: str, message: str, link: str = ""):
        """Send notification to ALL active users"""
        users = User.objects.filter(is_active=True)

        notifications = NotificationService.send_bulk_notifications(
            users=list(users),
            notification_type="system_announcement",
            title=title,
            message=message,
            link=link,
        )

        logger.info(f"📢 System announcement sent to {len(notifications)} users")
        return notifications

    @classmethod
    def notify_by_role(cls, role: str, title: str, message: str, link: str = ""):
        """Send notification to all users of a specific role"""
        users = User.objects.filter(role=role, is_active=True)

        notifications = NotificationService.send_bulk_notifications(
            users=list(users),
            notification_type="system_announcement",
            title=title,
            message=message,
            link=link,
        )

        logger.info(f"📢 Announcement sent to {len(notifications)} {role}s")
        return notifications


class DocumentNotificationService:
    """Service for document verification notifications"""

    @classmethod
    def notify_document_verified(cls, document, teacher: User):
        """Notify teacher when their document is verified"""
        NotificationService.send_notification(
            user=teacher,
            notification_type="document_verified",
            title="Document Verified ✅",
            message=f"Your {document.document_type} document has been verified by the admin.",
            link="/teacher/documents",
            metadata={
                "document_id": document.id,
                "document_type": document.document_type,
                "verified_at": (
                    document.verified_at.isoformat() if document.verified_at else None
                ),
            },
        )

    @classmethod
    def notify_document_rejected(cls, document, teacher: User, reason: str):
        """Notify teacher when their document is rejected"""
        NotificationService.send_notification(
            user=teacher,
            notification_type="document_rejected",
            title="Document Rejected ❌",
            message=f"Your {document.document_type} document was rejected. Reason: {reason}",
            link="/teacher/documents?resubmit=" + str(document.id),
            metadata={
                "document_id": document.id,
                "document_type": document.document_type,
                "rejection_reason": reason,
                "can_resubmit": True,
            },
        )

    @classmethod
    def notify_document_uploaded(cls, document, teacher: User):
        """Notify admins when a new document is uploaded"""
        from accounts.models import User

        admin_users = User.objects.filter(role="admin", is_active=True)

        notifications = NotificationService.send_bulk_notifications(
            users=list(admin_users),
            notification_type="document_uploaded",
            title="New Document for Verification",
            message=f"{teacher.email} uploaded a {document.document_type} document",
            link=f"/admin/documents/",
            metadata={
                "document_id": document.id,
                "document_type": document.document_type,
                "teacher_id": teacher.id,
                "teacher_email": teacher.email,
            },
        )

        logger.info(
            f"📨 Notified {len(notifications)} admins about new document upload"
        )
