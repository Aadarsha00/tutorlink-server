from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsAdmin
from notifications.services import NotificationService
from .models import UserReport
from .serializers import AdminReportUpdateSerializer, UserReportSerializer


class ReportCreateView(generics.CreateAPIView):
    serializer_class = UserReportSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        report = serializer.save()
        admins = report.__class__.objects.none()
        try:
            from accounts.models import User

            admins = User.objects.filter(role="admin", is_active=True)
        except Exception:
            admins = []

        for admin in admins:
            NotificationService.send_notification(
                user=admin,
                notification_type="system_announcement",
                title=f"New {report.category} report",
                message=report.title,
                link="/admin/reports",
                metadata={"report_id": report.id, "category": report.category},
            )


class AdminReportListView(generics.ListAPIView):
    serializer_class = UserReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def get_queryset(self):
        queryset = UserReport.objects.select_related("reporter", "assigned_to")
        status_value = self.request.query_params.get("status")
        category = self.request.query_params.get("category")
        target_type = self.request.query_params.get("target_type")
        if status_value and status_value != "all":
            queryset = queryset.filter(status=status_value)
        if category and category != "all":
            queryset = queryset.filter(category=category)
        if target_type and target_type != "all":
            queryset = queryset.filter(target_type=target_type)
        return queryset


class AdminReportDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin]

    def patch(self, request, pk):
        report = generics.get_object_or_404(UserReport, pk=pk)
        serializer = AdminReportUpdateSerializer(
            report, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserReportSerializer(report).data)
