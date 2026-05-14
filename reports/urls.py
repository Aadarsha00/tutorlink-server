from django.urls import path

from .views import AdminReportDetailView, AdminReportListView, ReportCreateView

urlpatterns = [
    path("", ReportCreateView.as_view(), name="report-create"),
    path("admin/", AdminReportListView.as_view(), name="admin-report-list"),
    path("admin/<int:pk>/", AdminReportDetailView.as_view(), name="admin-report-detail"),
]
