# applications/serializers.py
from rest_framework import serializers
from .models import Application
from gigs.models import Gig
from profiles.serializers import TeacherProfileSerializer, ParentProfileSerializer
from profiles.verification import teacher_documents_verified
from django.utils import timezone
from django.db.models import Q
from payments.models import PremiumSubscription
from payments.plans import APPLICATION_FREE_LIMIT


class ApplicationSerializer(serializers.ModelSerializer):
    teacher_profile = serializers.SerializerMethodField()
    parent_profile = serializers.SerializerMethodField()
    gig = serializers.PrimaryKeyRelatedField(queryset=Gig.objects.filter(status="open"))
    gig_details = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "gig",
            "gig_details",
            "teacher",
            "teacher_profile",
            "parent_profile",
            "cover_letter",
            "proposed_rate",
            "status",
            "selected_at",
            "response_deadline",
            "responded_at",
            "match_cancelled_at",
            "match_cancelled_by",
            "match_cancel_reason",
            "rate_change_proposed_rate",
            "rate_change_proposed_by",
            "rate_change_proposed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "teacher",
            "teacher_profile",
            "parent_profile",
            "gig_details",
            "status",
            "selected_at",
            "response_deadline",
            "responded_at",
            "match_cancelled_at",
            "match_cancelled_by",
            "match_cancel_reason",
            "rate_change_proposed_rate",
            "rate_change_proposed_by",
            "rate_change_proposed_at",
            "created_at",
            "updated_at",
        ]

    def get_teacher_profile(self, obj):
        """Get teacher profile with conditional contact hiding"""
        if hasattr(obj.teacher, "teacher_profile"):
            return TeacherProfileSerializer(
                obj.teacher.teacher_profile, context=self.context
            ).data
        return None

    def get_parent_profile(self, obj):
        """Get parent profile"""
        if hasattr(obj.gig.parent, "parent_profile"):
            return ParentProfileSerializer(obj.gig.parent.parent_profile).data
        return None

    def get_gig_details(self, obj):
        """Get detailed gig information"""
        gig = obj.gig
        return {
            "id": gig.id,
            "title": gig.title,
            "subject": gig.subject,
            "grade": gig.grade,
            "description": gig.description,
            "budget_min": float(gig.budget_min),
            "budget_max": float(gig.budget_max),
            "schedule": gig.schedule,
            "location": gig.location,
            "duration_weeks": gig.duration_weeks,
            "sessions_per_week": gig.sessions_per_week,
            "status": gig.status,
            "created_at": gig.created_at.isoformat(),
        }

    def validate(self, attrs):
        """Business rules validation"""
        request = self.context.get("request")
        user = request.user if request else None
        gig = attrs.get("gig")

        # Only teachers can apply
        if user and user.role != "teacher":
            raise serializers.ValidationError("Only teachers can apply for gigs.")

        if user and not teacher_documents_verified(user):
            raise serializers.ValidationError(
                "Your documents must be verified before you can apply for gigs."
            )

        # Prevent applying to own gig
        if gig and gig.parent == user:
            raise serializers.ValidationError("You cannot apply to your own gig.")

        # Check for duplicate applications
        if Application.objects.filter(gig=gig, teacher=user).exists():
            raise serializers.ValidationError("You have already applied to this gig.")

        has_active_premium = PremiumSubscription.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
            teacher=user,
            status="active",
        ).exists()

        if not has_active_premium:
            application_count = Application.objects.filter(teacher=user).count()
            if application_count >= APPLICATION_FREE_LIMIT:
                raise serializers.ValidationError(
                    {
                        "premium_required": (
                            f"You have used your {APPLICATION_FREE_LIMIT} free gig "
                            "applications. Subscribe to Premium to apply to more gigs."
                        ),
                        "free_application_limit": APPLICATION_FREE_LIMIT,
                    }
                )

        return attrs

    def create(self, validated_data):
        """Auto-assign teacher from request"""
        request = self.context.get("request")
        validated_data["teacher"] = request.user
        return super().create(validated_data)


class ApplicationListSerializer(serializers.ModelSerializer):
    gig = serializers.SerializerMethodField()
    teacher_profile = serializers.SerializerMethodField()
    parent_profile = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "id",
            "gig",
            "teacher",
            "teacher_profile",
            "parent_profile",
            "status",
            "proposed_rate",
            "created_at",
            "selected_at",
            "response_deadline",
            "responded_at",
            "match_cancelled_at",
            "match_cancelled_by",
            "match_cancel_reason",
            "rate_change_proposed_rate",
            "rate_change_proposed_by",
            "rate_change_proposed_at",
        ]

    def get_teacher_profile(self, obj):
        """Get teacher profile with conditional contact hiding"""
        if hasattr(obj.teacher, "teacher_profile"):
            return TeacherProfileSerializer(
                obj.teacher.teacher_profile, context=self.context
            ).data
        return None

    def get_parent_profile(self, obj):
        """Get parent profile"""
        if hasattr(obj.gig.parent, "parent_profile"):
            return ParentProfileSerializer(obj.gig.parent.parent_profile).data
        return None

    def get_gig(self, obj):
        return {
            "id": obj.gig.id,
            "title": obj.gig.title,
            "subject": obj.gig.subject,
            "grade": obj.gig.grade,
            "budget_min": float(obj.gig.budget_min),
            "budget_max": float(obj.gig.budget_max),
            "location": obj.gig.location,
            "status": obj.gig.status,
        }
