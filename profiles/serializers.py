# profiles/serializers.py
from rest_framework import serializers
from django.db.models import Avg
import os
from profiles.models import (
    TeacherProfile,
    ParentProfile,
    Rating,
    Subject,
    Grade,
    TeacherAvailability,
    VerificationDocument,
    ParentVerificationDocument,
)
from accounts.models import User
from gigs.models import Gig


# ============================================
# LOOKUP SERIALIZERS
# ============================================


class SubjectSerializer(serializers.ModelSerializer):
    """Serializer for Subject model"""

    class Meta:
        model = Subject
        fields = ["id", "name", "description", "is_active"]


class GradeSerializer(serializers.ModelSerializer):
    """Serializer for Grade model"""

    class Meta:
        model = Grade
        fields = ["id", "name", "order", "is_active"]


# ============================================
# USER SERIALIZERS
# ============================================


class UserSerializer(serializers.ModelSerializer):
    """Basic user serializer"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "role"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


# ============================================
# AVAILABILITY SERIALIZERS
# ============================================


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    """Serializer for teacher availability slots"""

    class Meta:
        model = TeacherAvailability
        fields = [
            "id",
            "day_of_week",
            "start_time",
            "end_time",
            "is_available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, data):
        """Ensure start_time is before end_time"""
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError("Start time must be before end time")

        return data


# ============================================
# DOCUMENT SERIALIZERS
# ============================================


class VerificationDocumentSerializer(serializers.ModelSerializer):
    """Serializer for teacher verification documents"""

    file_url = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    verified_by = serializers.SerializerMethodField()

    class Meta:
        model = VerificationDocument
        fields = [
            "id",
            "user",
            "document_type",
            "file_name",
            "file_url",
            "file_size",
            "uploaded_at",
            "verified",
            "verified_at",
            "verified_by",
            "rejection_reason",
            "notes",
        ]
        read_only_fields = [
            "id",
            "user",
            "file_name",
            "file_url",
            "file_size",
            "uploaded_at",
        ]

    def get_file_url(self, obj):
        """Get the full URL for the file"""
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        elif obj.file:
            return obj.file.url
        return None

    def get_user(self, obj):
        """Get document owner details"""
        user = obj.teacher.user
        profile_picture_url = None
        if getattr(user, "profile_picture", None):
            request = self.context.get("request")
            profile_picture_url = (
                request.build_absolute_uri(user.profile_picture.url)
                if request
                else user.profile_picture.url
            )
        return {
            "id": user.id,
            "email": user.email,
            "full_name": f"{user.first_name} {user.last_name}",
            "role": user.role,
            "profile_picture": profile_picture_url,
        }

    def get_verified_by(self, obj):
        """Get admin who verified the document"""
        if obj.verified_by:
            return {
                "id": obj.verified_by.id,
                "email": obj.verified_by.email,
            }
        return None


class ParentVerificationDocumentSerializer(serializers.ModelSerializer):
    """Serializer for parent verification documents"""

    file_url = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    verified_by = serializers.SerializerMethodField()

    class Meta:
        model = ParentVerificationDocument
        fields = [
            "id",
            "user",
            "document_type",
            "file_name",
            "file_url",
            "file_size",
            "uploaded_at",
            "verified",
            "verified_at",
            "verified_by",
            "rejection_reason",
            "notes",
        ]
        read_only_fields = [
            "id",
            "user",
            "file_name",
            "file_url",
            "file_size",
            "uploaded_at",
        ]

    def get_file_url(self, obj):
        """Get the full URL for the file"""
        request = self.context.get("request")
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        elif obj.file:
            return obj.file.url
        return None

    def get_user(self, obj):
        """Get document owner details"""
        user = obj.parent.user
        profile_picture_url = None
        if getattr(user, "profile_picture", None):
            request = self.context.get("request")
            profile_picture_url = (
                request.build_absolute_uri(user.profile_picture.url)
                if request
                else user.profile_picture.url
            )
        return {
            "id": user.id,
            "email": user.email,
            "full_name": f"{user.first_name} {user.last_name}",
            "role": user.role,
            "profile_picture": profile_picture_url,
        }

    def get_verified_by(self, obj):
        """Get admin who verified the document"""
        if obj.verified_by:
            return {
                "id": obj.verified_by.id,
                "email": obj.verified_by.email,
            }
        return None


class AdminProfilePictureSerializer(serializers.ModelSerializer):
    """Represent a user's profile picture as an admin-verifiable item."""

    user = serializers.SerializerMethodField()
    document_type = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    uploaded_at = serializers.DateTimeField(source="updated_at", read_only=True)
    verified = serializers.BooleanField(source="profile_picture_verified", read_only=True)
    verified_at = serializers.DateTimeField(
        source="profile_picture_verified_at", read_only=True
    )
    verified_by = serializers.SerializerMethodField()
    rejection_reason = serializers.CharField(
        source="profile_picture_rejection_reason", read_only=True
    )
    notes = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "user",
            "document_type",
            "file_name",
            "file_url",
            "file_size",
            "uploaded_at",
            "verified",
            "verified_at",
            "verified_by",
            "rejection_reason",
            "notes",
        ]

    def get_user(self, obj):
        return {
            "id": obj.id,
            "email": obj.email,
            "full_name": obj.get_full_name(),
            "role": obj.role,
            "profile_picture": self.get_file_url(obj),
        }

    def get_document_type(self, obj):
        return "profile_picture"

    def get_file_name(self, obj):
        if not obj.profile_picture:
            return ""
        return os.path.basename(obj.profile_picture.name)

    def get_file_url(self, obj):
        if not obj.profile_picture:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return obj.profile_picture.url

    def get_file_size(self, obj):
        if not obj.profile_picture:
            return 0
        try:
            return obj.profile_picture.size
        except OSError:
            return 0

    def get_verified_by(self, obj):
        if obj.profile_picture_verified_by:
            return {
                "id": obj.profile_picture_verified_by.id,
                "email": obj.profile_picture_verified_by.email,
            }
        return None

    def get_notes(self, obj):
        return ""


# ============================================
# PROFILE SERIALIZERS
# ============================================


class TeacherProfileSerializer(serializers.ModelSerializer):
    """
    Teacher profile serializer with conditional contact hiding
    """

    user = serializers.SerializerMethodField()
    subjects = serializers.SerializerMethodField()
    grades = serializers.SerializerMethodField()
    kyc_photo_url = serializers.SerializerMethodField()

    # Write-only fields for creating/updating
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    grade_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    kyc_photo = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = TeacherProfile
        fields = [
            "id",
            "user",
            "full_name",
            "phone",
            "citizenship_number",
            "education",
            "experience_years",
            "subjects",
            "grades",
            "subject_ids",  # Write-only
            "grade_ids",  # Write-only
            "location",
            "address",
            "hourly_rate_min",
            "hourly_rate_max",
            "bio",
            "kyc_photo",  # Write-only
            "kyc_photo_url",  # Read-only
            "kyc_photo_verified",
            "kyc_photo_rejection_reason",
            "verification_status",
            "is_premium",
            "premium_expires_at",
            "average_rating",
            "total_reviews",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "verification_status",
            "is_premium",
            "premium_expires_at",
            "average_rating",
            "total_reviews",
            "created_at",
            "updated_at",
            "kyc_photo_url",
            "kyc_photo_verified",
            "kyc_photo_rejection_reason",
        ]

    def get_user(self, obj):
        """Return user info, hiding sensitive details if needed"""
        user = obj.user
        request = self.context.get("request")

        base_data = {
            "id": user.id,
            "role": user.role,
            "full_name": user.get_full_name(),
            "profile_picture": self._profile_picture_url(user, request),
        }

        # Check if contact details should be hidden
        if self._should_hide_contact(obj, request):
            return base_data

        # Return full details if allowed
        return {
            **base_data,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }

    def _profile_picture_url(self, user, request):
        if not getattr(user, "profile_picture", None):
            return None
        if user.profile_picture_verified is not True:
            if not request or not request.user.is_authenticated:
                return None
            if request.user != user and request.user.role != "admin":
                return None
        if request:
            return request.build_absolute_uri(user.profile_picture.url)
        return user.profile_picture.url

    def get_kyc_photo_url(self, obj):
        """Return the full URL for the KYC photo"""
        if not obj.kyc_photo:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.kyc_photo.url)
        return obj.kyc_photo.url

    def get_subjects(self, obj):
        return [{"id": s.id, "name": s.name} for s in obj.subjects.all()]

    def get_grades(self, obj):
        return [{"id": g.id, "name": g.name} for g in obj.grades.all()]

    def validate_subject_ids(self, value):
        """Validate that all subject IDs exist"""
        if value:
            existing_ids = Subject.objects.filter(
                id__in=value, is_active=True
            ).values_list("id", flat=True)
            if len(existing_ids) != len(value):
                raise serializers.ValidationError("One or more subject IDs are invalid")
        return value

    def validate_grade_ids(self, value):
        """Validate that all grade IDs exist"""
        if value:
            existing_ids = Grade.objects.filter(
                id__in=value, is_active=True
            ).values_list("id", flat=True)
            if len(existing_ids) != len(value):
                raise serializers.ValidationError("One or more grade IDs are invalid")
        return value

    def validate(self, data):
        """Additional validation"""
        # Check that min rate is not greater than max rate
        hourly_rate_min = data.get("hourly_rate_min")
        hourly_rate_max = data.get("hourly_rate_max")

        if hourly_rate_min and hourly_rate_max and hourly_rate_min > hourly_rate_max:
            raise serializers.ValidationError(
                {"hourly_rate_min": "Minimum rate cannot be greater than maximum rate"}
            )

        # Ensure at least one subject is selected (for create)
        if self.instance is None:  # Creating new profile
            if not data.get("kyc_photo"):
                raise serializers.ValidationError(
                    {"kyc_photo": "KYC verification photo is required"}
                )
            if not data.get("citizenship_number"):
                raise serializers.ValidationError(
                    {"citizenship_number": "Citizenship number or NID is required"}
                )
            if not data.get("subject_ids"):
                raise serializers.ValidationError(
                    {"subject_ids": "At least one subject must be selected"}
                )
            if not data.get("grade_ids"):
                raise serializers.ValidationError(
                    {"grade_ids": "At least one grade must be selected"}
                )

        return data

    def create(self, validated_data):
        """Create profile with subjects and grades"""
        subject_ids = validated_data.pop("subject_ids", [])
        grade_ids = validated_data.pop("grade_ids", [])

        # Create the profile
        profile = TeacherProfile.objects.create(**validated_data)

        # Set many-to-many relationships
        if subject_ids:
            profile.subjects.set(subject_ids)
        if grade_ids:
            profile.grades.set(grade_ids)

        return profile

    def update(self, instance, validated_data):
        """Update profile with subjects and grades"""
        subject_ids = validated_data.pop("subject_ids", None)
        grade_ids = validated_data.pop("grade_ids", None)
        if "kyc_photo" in validated_data:
            validated_data["kyc_photo_verified"] = False
            validated_data["kyc_photo_rejection_reason"] = ""

        # Update regular fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update many-to-many relationships if provided
        if subject_ids is not None:
            instance.subjects.set(subject_ids)
        if grade_ids is not None:
            instance.grades.set(grade_ids)

        return instance

    def to_representation(self, instance):
        """Override to conditionally hide contact details"""
        data = super().to_representation(instance)
        request = self.context.get("request")

        if self._should_hide_contact(instance, request):
            # Hide sensitive information
            data["phone"] = None
            data["address"] = "****** (Hidden until payment)"
            data["location"] = (
                instance.location.split(",")[0]
                if "," in instance.location
                else instance.location
            )

        return data

    def _should_hide_contact(self, teacher_profile, request):
        """
        Determine if contact details should be hidden
        Hide if:
        1. User is a parent
        2. There's a gig in payment_pending or earlier status
        3. Payment has not been completed
        """
        if not request or not request.user.is_authenticated:
            return True

        # Don't hide for the teacher themselves
        if request.user == teacher_profile.user:
            return False

        # Don't hide for admins
        if request.user.role == "admin":
            return False

        # Check if requesting user is a parent with unpaid gig
        if request.user.role == "parent":
            from gigs.models import Gig
            from payments.models import GigPayment

            # Find gigs where this teacher is hired by this parent
            gigs = Gig.objects.filter(
                parent=request.user,
                hired_teacher=teacher_profile.user,
                status__in=[
                    "draft",
                    "open",
                    "selection_pending",
                    "confirmation_pending",
                    "payment_pending",
                ],
            )

            for gig in gigs:
                # Check if payment is completed
                try:
                    payment = GigPayment.objects.get(gig=gig)
                    if payment.status != "completed":
                        return True
                except GigPayment.DoesNotExist:
                    return True

        # For teachers viewing other teachers, hide contact
        if request.user.role == "teacher":
            return True

        return False


class ParentProfileSerializer(serializers.ModelSerializer):
    """Parent profile serializer"""

    user = serializers.SerializerMethodField()
    kyc_photo_url = serializers.SerializerMethodField()
    kyc_photo = serializers.ImageField(write_only=True, required=False)

    class Meta:
        model = ParentProfile
        fields = [
            "id",
            "user",
            "full_name",
            "phone",
            "citizenship_number",
            "location",
            "address",
            "kyc_photo",  # Write-only
            "kyc_photo_url",  # Read-only
            "kyc_photo_verified",
            "kyc_photo_rejection_reason",
            "average_rating",
            "total_reviews",
            "created_at",
            "updated_at",
        ]

    def get_kyc_photo_url(self, obj):
        """Return the full URL for the KYC photo"""
        if not obj.kyc_photo:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(obj.kyc_photo.url)
        return obj.kyc_photo.url

    def get_user(self, obj):
        """Return user info"""
        user = obj.user
        return {
            "id": user.id,
            "email": user.email,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.get_full_name(),
        }

    def validate(self, data):
        if self.instance is None:
            if not data.get("kyc_photo"):
                raise serializers.ValidationError(
                    {"kyc_photo": "KYC verification photo is required"}
                )
            if not data.get("citizenship_number"):
                raise serializers.ValidationError(
                    {"citizenship_number": "Citizenship number or NID is required"}
                )
        return data

    def update(self, instance, validated_data):
        if "kyc_photo" in validated_data:
            validated_data["kyc_photo_verified"] = False
            validated_data["kyc_photo_rejection_reason"] = ""
        return super().update(instance, validated_data)


# ============================================
# RATING SERIALIZERS
# ============================================


class RaterSerializer(serializers.ModelSerializer):
    """Minimal user info for rater/ratee"""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "role"]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


class RatingSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating ratings"""

    rater = RaterSerializer(read_only=True)
    ratee = RaterSerializer(read_only=True)
    rater_name = serializers.SerializerMethodField()
    ratee_name = serializers.SerializerMethodField()
    gig_title = serializers.SerializerMethodField()

    class Meta:
        model = Rating
        fields = [
            "id",
            "rater",
            "ratee",
            "rater_name",
            "ratee_name",
            "gig",
            "gig_title",
            "rater_type",
            "score",
            "review",
            "created_at",
        ]
        read_only_fields = ["id", "rater", "ratee", "rater_type", "created_at"]

    def get_rater_name(self, obj):
        return (
            f"{obj.rater.first_name} {obj.rater.last_name}".strip() or obj.rater.email
        )

    def get_ratee_name(self, obj):
        return (
            f"{obj.ratee.first_name} {obj.ratee.last_name}".strip() or obj.ratee.email
        )

    def get_gig_title(self, obj):
        return obj.gig.title if obj.gig else None

    def validate_score(self, value):
        """Ensure score is between 1 and 5"""
        if value < 1 or value > 5:
            raise serializers.ValidationError("Score must be between 1 and 5")
        return value

    def validate(self, data):
        """Validate rating creation"""
        request = self.context.get("request")
        gig = data.get("gig")

        if not gig:
            raise serializers.ValidationError("Gig is required")

        # Check if gig is completed
        if gig.status != "completed":
            raise serializers.ValidationError("Can only rate completed gigs")

        # Determine rater type and ratee
        if request.user.role == "parent":
            if gig.parent != request.user:
                raise serializers.ValidationError("You are not the parent of this gig")
            if not gig.hired_teacher:
                raise serializers.ValidationError("No teacher was hired for this gig")
            data["ratee"] = gig.hired_teacher
            data["rater_type"] = "parent"

        elif request.user.role == "teacher":
            if gig.hired_teacher != request.user:
                raise serializers.ValidationError("You were not hired for this gig")
            data["ratee"] = gig.parent
            data["rater_type"] = "teacher"

        else:
            raise serializers.ValidationError("Only parents and teachers can rate")

        # Check if already rated
        if Rating.objects.filter(rater=request.user, gig=gig).exists():
            raise serializers.ValidationError("You have already rated this gig")

        return data

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["rater"] = request.user
        return super().create(validated_data)


class UserRatingStatsSerializer(serializers.Serializer):
    """Statistics about a user's ratings"""

    user_id = serializers.IntegerField()
    average_rating = serializers.FloatField()
    total_ratings = serializers.IntegerField()
    rating_distribution = serializers.DictField()
    recent_ratings = RatingSerializer(many=True)
