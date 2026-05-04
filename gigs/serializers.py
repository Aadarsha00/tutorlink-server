# gigs/serializers.py
from rest_framework import serializers
from .models import Gig
from applications.models import Application
from accounts.models import User
from profiles.serializers import ParentProfileSerializer
from profiles.verification import parent_documents_verified

from django.utils import timezone


class GigSerializer(serializers.ModelSerializer):
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    parent_profile = serializers.SerializerMethodField()
    selected_teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="teacher"),
        required=False,
        allow_null=True,
    )
    hired_teacher = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role="teacher"),
        required=False,
        allow_null=True,
    )
    applications_count = serializers.SerializerMethodField(read_only=True)

    progress_percentage = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Gig
        fields = [
            "id",
            "parent",
            "parent_profile",
            "title",
            "subject",
            "grade",
            "description",
            "budget_min",
            "budget_max",
            "schedule",
            "location",
            "duration_weeks",
            "sessions_per_week",
            "status",
            "selected_teacher",
            "hired_teacher",
            "applications_count",
            "progress_percentage",
            "days_remaining",
            "created_at",
            "updated_at",
            "published_at",
            "closed_at",
        ]
        read_only_fields = [
            "id",
            "parent",
            "parent_profile",
            "applications_count",
            "progress_percentage",
            "days_remaining",
            "created_at",
            "updated_at",
            "published_at",
            "closed_at",
        ]

    def _get_start_date(self, obj):
        return obj.published_at or obj.created_at

    def get_progress_percentage(self, obj):
        if obj.status != "active":
            return 0

        start_date = self._get_start_date(obj)
        total_days = obj.duration_weeks * 7
        elapsed_days = (timezone.now() - start_date).days

        if total_days <= 0:
            return 0

        progress = (elapsed_days / total_days) * 100
        return max(0, min(100, round(progress)))

    def get_days_remaining(self, obj):
        if obj.status != "active":
            return 0

        start_date = self._get_start_date(obj)
        total_days = obj.duration_weeks * 7
        elapsed_days = (timezone.now() - start_date).days

        return max(0, total_days - elapsed_days)

    def get_parent_profile(self, obj):
        if hasattr(obj.parent, "parent_profile"):
            return ParentProfileSerializer(obj.parent.parent_profile).data
        return None

    def get_applications_count(self, obj):
        return obj.applications.count()

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        if user and user.role == "parent" and not parent_documents_verified(user):
            raise serializers.ValidationError(
                "Your documents must be verified before you can create gigs."
            )

        return attrs


class GigListSerializer(serializers.ModelSerializer):
    applications_count = serializers.SerializerMethodField()
    parent_profile = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Gig
        fields = [
            "id",
            "parent",
            "parent_profile",
            "title",
            "subject",
            "grade",
            "budget_min",
            "budget_max",
            "duration_weeks",
            "sessions_per_week",
            "location",
            "status",
            "created_at",
            "applications_count",
            "progress_percentage",
            "days_remaining",
        ]

    def _get_start_date(self, obj):
        return obj.published_at or obj.created_at

    def get_progress_percentage(self, obj):
        if obj.status != "active":
            return 0

        start_date = self._get_start_date(obj)
        total_days = obj.duration_weeks * 7
        elapsed_days = (timezone.now() - start_date).days

        if total_days <= 0:
            return 0

        return max(0, min(100, round((elapsed_days / total_days) * 100)))

    def get_days_remaining(self, obj):
        if obj.status != "active":
            return 0

        start_date = self._get_start_date(obj)
        total_days = obj.duration_weeks * 7
        elapsed_days = (timezone.now() - start_date).days

        return max(0, total_days - elapsed_days)

    def get_parent_profile(self, obj):
        if hasattr(obj.parent, "parent_profile"):
            profile = obj.parent.parent_profile
            return {
                "id": profile.id,
                "full_name": profile.full_name,
                "location": profile.location,
                "address": profile.address,
                "average_rating": profile.average_rating,
                "total_reviews": profile.total_reviews,
            }
        return None

    def get_applications_count(self, obj):
        return obj.applications.count()
