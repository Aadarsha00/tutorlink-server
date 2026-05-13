from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessagesView,
    ConversationReadView,
    MessagingUnreadCountView,
)

urlpatterns = [
    path("conversations/", ConversationListView.as_view(), name="conversation-list"),
    path(
        "conversations/<int:pk>/",
        ConversationDetailView.as_view(),
        name="conversation-detail",
    ),
    path(
        "conversations/<int:pk>/messages/",
        ConversationMessagesView.as_view(),
        name="conversation-messages",
    ),
    path(
        "conversations/<int:pk>/read/",
        ConversationReadView.as_view(),
        name="conversation-read",
    ),
    path("unread-count/", MessagingUnreadCountView.as_view(), name="messaging-unread"),
]
