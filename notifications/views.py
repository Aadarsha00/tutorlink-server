from django.conf import settings
from django.core.mail import send_mail
from django.utils.dateparse import parse_date
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from accounts.permissions import IsAdmin
from .models import Notification
from .serializers import NotificationSerializer
from .services import NotificationService


class NotificationListView(generics.ListAPIView):
    """
    List notifications for logged-in user
    """

    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class UnreadNotificationCountView(APIView):
    """
    Get unread notification count
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = NotificationService.get_unread_count(request.user)
        return Response({"unread_count": count})


class MarkNotificationReadView(APIView):
    """
    Mark a single notification as read
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        success = NotificationService.mark_as_read(pk, request.user)
        if not success:
            return Response(
                {"detail": "Notification not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"success": True})


class MarkAllNotificationsReadView(APIView):
    """
    Mark all notifications as read
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        count = NotificationService.mark_all_as_read(request.user)
        return Response({"marked_count": count})


class AdminBroadcastNotificationView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def post(self, request):
        title = (request.data.get("title") or "").strip()
        message = (request.data.get("message") or "").strip()
        link = (request.data.get("link") or "").strip()
        audience = request.data.get("audience") or "all"
        roles = request.data.get("roles") or []
        user_ids = request.data.get("user_ids") or []
        emails = request.data.get("emails") or []
        active_only = request.data.get("active_only", True)
        joined_after = request.data.get("joined_after") or ""
        joined_before = request.data.get("joined_before") or ""

        if not title or not message:
            return Response(
                {"error": "Title and message are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        users = User.objects.all()
        if active_only:
            users = users.filter(is_active=True)

        if audience == "roles":
            users = users.filter(role__in=roles)
        elif audience == "users":
            users = users.filter(id__in=user_ids)
        elif audience != "all":
            return Response(
                {"error": "Audience must be all, roles, or users"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        after_date = parse_date(joined_after)
        before_date = parse_date(joined_before)
        if after_date:
            users = users.filter(created_at__date__gte=after_date)
        if before_date:
            users = users.filter(created_at__date__lte=before_date)

        user_list = list(users.distinct())
        notifications = NotificationService.send_bulk_notifications(
            users=user_list,
            notification_type="system_announcement",
            title=title,
            message=message,
            link=link,
            metadata={
                "sent_by": request.user.id,
                "audience": audience,
                "roles": roles,
                "criteria": {
                    "active_only": active_only,
                    "joined_after": joined_after,
                    "joined_before": joined_before,
                },
            },
        )

        sent_emails = 0
        email_list = [email.strip() for email in emails if email and email.strip()]
        if email_list:
            sent_emails = send_mail(
                subject=title,
                message=message,
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                recipient_list=email_list,
                fail_silently=True,
            )

        return Response(
            {
                "created_count": len(notifications),
                "matched_users": len(user_list),
                "email_count": sent_emails,
            }
        )
