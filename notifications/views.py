from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

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
