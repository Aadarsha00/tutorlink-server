from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Notification
import logging
from .services import PremiumNotificationService

logger = logging.getLogger(__name__)


@shared_task
def send_notification_email(notification_id: int):
    """Send email for a notification"""
    try:
        notification = Notification.objects.select_related("user").get(
            id=notification_id
        )

        # Render email template
        html_message = render_to_string(
            "emails/notification.html",
            {
                "notification": notification,
                "user": notification.user,
                "site_url": settings.FRONTEND_URL,
            },
        )

        # Send email
        send_mail(
            subject=notification.title,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.user.email],
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Email sent for notification {notification_id}")

    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as e:
        logger.error(f"Failed to send email for notification {notification_id}: {e}")


@shared_task
def cleanup_old_notifications():
    """Periodic task to clean up old notifications"""
    from .services import NotificationService

    count = NotificationService.delete_old_notifications(days=90)
    logger.info(f"Cleaned up {count} old notifications")
    return count


@shared_task
def check_premium_expiration():
    """Check and notify users about expiring premium subscriptions"""
    from django.utils import timezone
    from datetime import timedelta
    from payments.models import PremiumSubscription
    from accounts.models import User

    # Find subscriptions expiring in 3 days
    expiring_soon = timezone.now() + timedelta(days=3)

    subscriptions = PremiumSubscription.objects.filter(
        status="active", expires_at__lte=expiring_soon, expires_at__gte=timezone.now()
    ).select_related("teacher")

    for subscription in subscriptions:
        PremiumNotificationService.notify_premium_expiring(
            subscription.teacher, subscription
        )

    # Find expired subscriptions
    expired_subscriptions = PremiumSubscription.objects.filter(
        status="active", expires_at__lt=timezone.now()
    ).select_related("teacher")

    for subscription in expired_subscriptions:
        # Update status
        subscription.status = "expired"
        subscription.save()

        # Update teacher profile
        teacher_profile = subscription.teacher.teacher_profile
        teacher_profile.is_premium = False
        teacher_profile.save()

        # Notify
        PremiumNotificationService.notify_premium_expired(subscription.teacher)

    logger.info(
        f"Processed {subscriptions.count()} expiring and "
        f"{expired_subscriptions.count()} expired subscriptions"
    )
