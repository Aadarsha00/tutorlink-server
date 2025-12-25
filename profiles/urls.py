from django.urls import path
from .views import teacher_stats, parent_stats, admin_stats

urlpatterns = [
    path("teacher/stats/", teacher_stats, name="teacher-stats"),
    path("parent/stats/", parent_stats, name="parent-stats"),
    path("admin/stats/", admin_stats, name="admin-stats"),
]
