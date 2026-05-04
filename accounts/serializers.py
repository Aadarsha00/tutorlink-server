# accounts/serializers.py

from django.contrib.auth import get_user_model
from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class VerifiedTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Require email activation before issuing JWT tokens."""

    def validate(self, attrs):
        login_value = attrs.get(self.username_field)
        password = attrs.get("password")
        if login_value:
            lookup = {f"{self.username_field}__iexact": login_value}
            user = get_user_model().objects.filter(**lookup).first()

            if not user or not user.is_active:
                raise AuthenticationFailed(
                    "No active account found with the given credentials",
                    code="no_active_account",
                )

            if not user.check_password(password):
                raise AuthenticationFailed(
                    "Invalid Credentials",
                    code="invalid_credentials",
                )

            if not user.is_email_verified:
                raise AuthenticationFailed(
                    "Please verify your email before logging in.",
                    code="email_not_verified",
                )

        data = super().validate(attrs)

        if not self.user.is_email_verified:
            raise AuthenticationFailed(
                "Please verify your email before logging in.",
                code="email_not_verified",
            )

        return data


class UserCreateSerializer(BaseUserCreateSerializer):
    """
    Serializer for user registration
    Extends Djoser's UserCreateSerializer to include role field
    """

    class Meta(BaseUserCreateSerializer.Meta):
        model = User
        fields = ("id", "email", "password", "role", "first_name", "last_name")
        extra_kwargs = {
            "password": {"write_only": True},
        }

    def validate_role(self, value):
        """Validate that role is one of the allowed choices"""
        allowed_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if value not in allowed_roles:
            raise serializers.ValidationError(
                f"Invalid role. Must be one of: {', '.join(allowed_roles)}"
            )
        return value

    def validate_email(self, value):
        """Validate email format and uniqueness"""
        value = value.lower()
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value


class UserSerializer(BaseUserSerializer):
    """
    Serializer for displaying user data
    Used for GET requests to show user information
    """

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = (
            "id",
            "email",
            "role",
            "first_name",
            "last_name",
            "profile_picture",
            "profile_picture_verified",
            "profile_picture_rejection_reason",
            "is_active",
            "is_email_verified",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "email",
            "is_active",
            "is_email_verified",
            "profile_picture_verified",
            "profile_picture_rejection_reason",
            "created_at",
            "updated_at",
        )

    def _id_documents_verified(self, user):
        if user.role == "admin":
            return True

        required_types = ("citizenship_front", "citizenship_back")

        if user.role == "teacher":
            from profiles.models import TeacherProfile, VerificationDocument

            try:
                profile = TeacherProfile.objects.get(user=user)
            except TeacherProfile.DoesNotExist:
                return False

            documents = VerificationDocument.objects.filter(
                teacher=profile,
                document_type__in=required_types,
            ).order_by("-uploaded_at")
        elif user.role == "parent":
            from profiles.models import ParentProfile, ParentVerificationDocument

            try:
                profile = ParentProfile.objects.get(user=user)
            except ParentProfile.DoesNotExist:
                return False

            documents = ParentVerificationDocument.objects.filter(
                parent=profile,
                document_type__in=required_types,
            ).order_by("-uploaded_at")
        else:
            return False

        latest = {}
        for document in documents:
            latest.setdefault(document.document_type, document)

        return all(
            latest.get(document_type) and latest[document_type].verified is True
            for document_type in required_types
        )

    def update(self, instance, validated_data):
        identity_fields = {"first_name", "last_name", "profile_picture"}
        if identity_fields.intersection(validated_data) and not self._id_documents_verified(
            instance
        ):
            raise serializers.ValidationError(
                {
                    "detail": (
                        "Profile information can be changed only after "
                        "citizenship front and back are verified."
                    )
                }
            )

        if "profile_picture" in validated_data:
            instance.profile_picture_verified = None
            instance.profile_picture_rejection_reason = ""
            instance.profile_picture_verified_at = None
            instance.profile_picture_verified_by = None
        return super().update(instance, validated_data)


class CurrentUserSerializer(UserSerializer):
    """
    Serializer for the currently authenticated user
    Shows additional details for /auth/users/me/ endpoint
    """

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_active",
            "is_email_verified",
            "created_at",
            "updated_at",
        )
