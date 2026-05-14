from django.utils import timezone
from rest_framework import serializers

from accounts.models import User
from .models import UserReport


def user_summary(user):
    if not user:
        return None
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.get_full_name() or user.email,
        "role": user.role,
    }


class UserReportSerializer(serializers.ModelSerializer):
    reporter = serializers.SerializerMethodField()
    assigned_to = serializers.SerializerMethodField()

    class Meta:
        model = UserReport
        fields = [
            "id",
            "reporter",
            "reporter_email",
            "category",
            "target_type",
            "target_id",
            "target_label",
            "page_url",
            "title",
            "description",
            "status",
            "priority",
            "assigned_to",
            "resolution_note",
            "metadata",
            "created_at",
            "updated_at",
            "resolved_at",
        ]
        read_only_fields = [
            "id",
            "reporter",
            "status",
            "priority",
            "assigned_to",
            "resolution_note",
            "metadata",
            "created_at",
            "updated_at",
            "resolved_at",
        ]

    def get_reporter(self, obj):
        return user_summary(obj.reporter)

    def get_assigned_to(self, obj):
        return user_summary(obj.assigned_to)

    def validate(self, attrs):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            if not attrs.get("reporter_email"):
                raise serializers.ValidationError(
                    {"reporter_email": "Email is required for guest reports."}
                )
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["reporter"] = request.user
            validated_data.setdefault("reporter_email", request.user.email)
        return super().create(validated_data)


class AdminReportUpdateSerializer(serializers.ModelSerializer):
    assigned_to_id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = UserReport
        fields = ["status", "priority", "assigned_to_id", "resolution_note"]

    def validate_assigned_to_id(self, value):
        if value is None:
            return None
        if not User.objects.filter(id=value, role="admin").exists():
            raise serializers.ValidationError("Assignee must be an admin user.")
        return value

    def update(self, instance, validated_data):
        assigned_to_id = validated_data.pop("assigned_to_id", serializers.empty)
        if assigned_to_id is not serializers.empty:
            instance.assigned_to_id = assigned_to_id

        status_value = validated_data.get("status")
        if status_value in {"resolved", "dismissed"} and not instance.resolved_at:
            instance.resolved_at = timezone.now()
        elif status_value in {"open", "in_review"}:
            instance.resolved_at = None

        return super().update(instance, validated_data)
