from django.contrib import admin

from .models import BlockedMessageAttempt, Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["id", "gig", "parent", "teacher", "is_active", "updated_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["gig__title", "parent__email", "teacher__email"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "sender", "created_at", "read_at"]
    list_filter = ["created_at", "read_at"]
    search_fields = ["body", "sender__email", "conversation__gig__title"]


@admin.register(BlockedMessageAttempt)
class BlockedMessageAttemptAdmin(admin.ModelAdmin):
    list_display = ["id", "conversation", "sender", "reason", "created_at"]
    list_filter = ["reason", "created_at"]
    search_fields = ["body", "sender__email", "conversation__gig__title"]

# Register your models here.
