from django.urls import path
from .views import (
    NotificationListView,
    UnreadNotificationCountView,
    MarkNotificationReadView,
    MarkAllNotificationsReadView,
)

urlpatterns = [
    path("", NotificationListView.as_view(), name="notifications-list"),
    path(
        "unread-count/",
        UnreadNotificationCountView.as_view(),
        name="notifications-unread-count",
    ),
    path(
        "<int:pk>/read/", MarkNotificationReadView.as_view(), name="notifications-read"
    ),
    path(
        "read-all/",
        MarkAllNotificationsReadView.as_view(),
        name="notifications-read-all",
    ),
]
