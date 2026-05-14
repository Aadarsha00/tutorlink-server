from rest_framework import serializers
from .models import PremiumSubscription, GigPayment, GigBoostPayment


class PremiumSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for premium subscriptions"""

    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = PremiumSubscription
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "plan_id",
            "billing_cycle",
            "amount",
            "duration_days",
            "starts_at",
            "expires_at",
            "status",
            "khalti_pidx",
            "khalti_transaction_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "teacher",
            "plan_id",
            "billing_cycle",
            "starts_at",
            "expires_at",
            "status",
            "khalti_transaction_id",
            "created_at",
            "updated_at",
        ]

    def get_teacher_name(self, obj):
        return (
            f"{obj.teacher.first_name} {obj.teacher.last_name}".strip()
            or obj.teacher.email
        )


class GigPaymentSerializer(serializers.ModelSerializer):
    gig_title = serializers.CharField(source="gig.title", read_only=True)
    parent_name = serializers.CharField(source="parent.full_name", read_only=True)
    teacher_name = serializers.CharField(source="teacher.get_full_name", read_only=True)

    class Meta:
        model = GigPayment
        fields = [
            "id",
            "gig",
            "gig_title",
            "parent",
            "parent_name",
            "teacher",
            "teacher_name",
            "amount",
            "platform_fee",
            "status",
            "khalti_pidx",
            "khalti_transaction_id",
            "created_at",
            "paid_at",
        ]


class GigBoostPaymentSerializer(serializers.ModelSerializer):
    gig_title = serializers.CharField(source="gig.title", read_only=True)
    parent_name = serializers.CharField(source="parent.full_name", read_only=True)

    class Meta:
        model = GigBoostPayment
        fields = [
            "id",
            "gig",
            "gig_title",
            "parent",
            "parent_name",
            "plan_id",
            "amount",
            "duration_days",
            "status",
            "khalti_pidx",
            "khalti_transaction_id",
            "starts_at",
            "expires_at",
            "created_at",
            "paid_at",
        ]
        read_only_fields = [
            "id",
            "parent",
            "teacher",
            "platform_fee",
            "status",
            "khalti_pidx",
            "khalti_transaction_id",
            "created_at",
            "paid_at",
        ]
        read_only_fields = [
            "id",
            "parent",
            "amount",
            "duration_days",
            "status",
            "khalti_pidx",
            "khalti_transaction_id",
            "starts_at",
            "expires_at",
            "created_at",
            "paid_at",
        ]
