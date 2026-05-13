from rest_framework import serializers

from applications.models import Application
from .models import Conversation, Message


def profile_picture_url(user, request=None):
    if not user.profile_picture:
        return None

    url = user.profile_picture.url
    if request:
        return request.build_absolute_uri(url)
    return url


def user_payload(user, request=None):
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "full_name": user.get_full_name() or user.email,
        "role": user.role,
        "profile_picture": profile_picture_url(user, request),
    }


class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ["id", "conversation", "sender", "body", "read_at", "created_at"]
        read_only_fields = fields

    def get_sender(self, obj):
        return user_payload(obj.sender, self.context.get("request"))


class ConversationSerializer(serializers.ModelSerializer):
    gig = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    teacher = serializers.SerializerMethodField()
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    matched_application_id = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "gig",
            "parent",
            "teacher",
            "other_user",
            "is_active",
            "matched_application_id",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_gig(self, obj):
        return {
            "id": obj.gig.id,
            "title": obj.gig.title,
            "subject": obj.gig.subject,
            "grade": obj.gig.grade,
            "status": obj.gig.status,
        }

    def get_matched_application_id(self, obj):
        return (
            Application.objects.filter(
                gig=obj.gig,
                teacher=obj.teacher,
                status="accepted",
            )
            .values_list("id", flat=True)
            .first()
        )

    def get_parent(self, obj):
        return user_payload(obj.parent, self.context.get("request"))

    def get_teacher(self, obj):
        return user_payload(obj.teacher, self.context.get("request"))

    def get_other_user(self, obj):
        request = self.context.get("request")
        if not request:
            return None
        other = obj.other_participant(request.user)
        return user_payload(other, request) if other else None

    def get_last_message(self, obj):
        message = obj.messages.order_by("-created_at").first()
        if not message:
            return None
        return MessageSerializer(message, context=self.context).data

    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request:
            return 0
        return obj.messages.filter(read_at__isnull=True).exclude(sender=request.user).count()


class SendMessageSerializer(serializers.Serializer):
    body = serializers.CharField(max_length=2000, trim_whitespace=True)
