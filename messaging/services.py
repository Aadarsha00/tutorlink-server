from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from notifications.services import NotificationService

from .moderation import validate_message_body
from .models import BlockedMessageAttempt, Conversation, Message

CHAT_OPEN_STATUSES = {"payment_pending", "active", "completed", "disputed"}


class ConversationService:
    @classmethod
    @transaction.atomic
    def get_or_create_for_gig(cls, gig):
        if not gig.parent_id or not gig.hired_teacher_id:
            raise ValueError("Gig must have a parent and hired teacher before chat opens.")

        if gig.status not in CHAT_OPEN_STATUSES:
            raise ValueError("Chat can only open after both sides accept the match.")

        conversation, created = Conversation.objects.get_or_create(
            gig=gig,
            defaults={
                "parent": gig.parent,
                "teacher": gig.hired_teacher,
                "is_active": True,
            },
        )

        changed = False
        if conversation.parent_id != gig.parent_id:
            conversation.parent = gig.parent
            changed = True
        if conversation.teacher_id != gig.hired_teacher_id:
            conversation.teacher = gig.hired_teacher
            changed = True
        if not conversation.is_active:
            conversation.is_active = True
            conversation.closed_at = None
            changed = True

        if changed:
            conversation.save()

        return conversation, created

    @classmethod
    def for_user(cls, user):
        return (
            Conversation.objects.filter(Q(parent=user) | Q(teacher=user))
            .select_related("gig", "parent", "teacher")
            .prefetch_related("messages")
        )

    @classmethod
    def close_for_gig(cls, gig):
        return Conversation.objects.filter(gig=gig, is_active=True).update(
            is_active=False,
            closed_at=timezone.now(),
            updated_at=timezone.now(),
        )


class MessageService:
    @classmethod
    @transaction.atomic
    def send_message(cls, conversation, sender, body):
        if not conversation.has_participant(sender):
            raise PermissionDenied("You do not have access to this conversation.")

        if not conversation.is_active:
            raise ValidationError("This conversation is closed.")

        if conversation.gig.status not in CHAT_OPEN_STATUSES:
            conversation.is_active = False
            conversation.closed_at = timezone.now()
            conversation.save(update_fields=["is_active", "closed_at", "updated_at"])
            raise ValidationError(
                "This conversation is closed because the gig is no longer active."
            )

        moderation = validate_message_body(body)
        cleaned_body = (body or "").strip()

        if not moderation.allowed:
            BlockedMessageAttempt.objects.create(
                conversation=conversation,
                sender=sender,
                body=cleaned_body,
                reason=moderation.reason,
            )
            raise ValidationError(
                {
                    "error": moderation.message,
                    "reason": moderation.reason,
                }
            )

        message = Message.objects.create(
            conversation=conversation,
            sender=sender,
            body=cleaned_body,
        )

        conversation.last_message_at = message.created_at
        conversation.save(update_fields=["last_message_at", "updated_at"])

        receiver = conversation.other_participant(sender)
        if receiver:
            NotificationService.send_notification(
                user=receiver,
                notification_type="message_received",
                title="New message",
                message=f"{sender.get_full_name() or sender.email} sent you a message about {conversation.gig.title}.",
                link=f"/messages?conversation={conversation.id}",
                metadata={
                    "conversation_id": conversation.id,
                    "message_id": message.id,
                    "gig_id": conversation.gig_id,
                    "sender_id": sender.id,
                },
            )

        return message

    @classmethod
    def mark_read(cls, conversation, user):
        if not conversation.has_participant(user):
            raise PermissionDenied("You do not have access to this conversation.")

        read_at = timezone.now()
        queryset = Message.objects.filter(
            conversation=conversation,
            read_at__isnull=True,
        ).exclude(sender=user)
        message_ids = list(queryset.values_list("id", flat=True))
        marked_count = queryset.update(read_at=read_at)

        return {
            "marked_count": marked_count,
            "message_ids": message_ids,
            "read_at": read_at.isoformat() if marked_count else None,
        }
