from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListView,
    ConversationMessagesView,
    ConversationReadView,
    MessagingUnreadCountView,
    AdminConversationListView,
    AdminConversationMessagesView,
    AdminMessageDeleteView,
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
    path(
        "admin/conversations/",
        AdminConversationListView.as_view(),
        name="admin-conversation-list",
    ),
    path(
        "admin/conversations/<int:pk>/messages/",
        AdminConversationMessagesView.as_view(),
        name="admin-conversation-messages",
    ),
    path(
        "admin/conversations/<int:pk>/messages/<int:message_id>/",
        AdminMessageDeleteView.as_view(),
        name="admin-message-delete",
    ),
]
