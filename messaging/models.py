from django.conf import settings
from django.db import models


class Conversation(models.Model):
    gig = models.OneToOneField(
        "gigs.Gig", on_delete=models.CASCADE, related_name="conversation"
    )
    parent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="parent_conversations",
    )
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="teacher_conversations",
    )
    is_active = models.BooleanField(default=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_message_at", "-updated_at"]
        indexes = [
            models.Index(fields=["parent", "is_active", "-updated_at"]),
            models.Index(fields=["teacher", "is_active", "-updated_at"]),
        ]

    def __str__(self):
        return f"Conversation for {self.gig.title}"

    def has_participant(self, user):
        return user.is_authenticated and user.id in {self.parent_id, self.teacher_id}

    def other_participant(self, user):
        if user.id == self.parent_id:
            return self.teacher
        if user.id == self.teacher_id:
            return self.parent
        return None


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_messages"
    )
    body = models.TextField(max_length=2000)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
            models.Index(fields=["conversation", "sender", "read_at"]),
        ]

    def __str__(self):
        return f"Message {self.id} in conversation {self.conversation_id}"


class BlockedMessageAttempt(models.Model):
    REASON_CHOICES = [
        ("phone_number", "Phone Number"),
        ("external_contact", "External Contact"),
        ("off_platform_payment", "Off-platform Payment"),
        ("location_sharing", "Location Sharing"),
        ("empty", "Empty Message"),
        ("too_long", "Too Long"),
    ]

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="blocked_attempts"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_message_attempts",
    )
    body = models.TextField()
    reason = models.CharField(max_length=40, choices=REASON_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["conversation", "-created_at"]),
            models.Index(fields=["sender", "-created_at"]),
        ]

# Create your models here.
