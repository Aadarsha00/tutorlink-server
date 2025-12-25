# accounts/serializers.py

from djoser.serializers import UserCreateSerializer as BaseUserCreateSerializer
from djoser.serializers import UserSerializer as BaseUserSerializer
from rest_framework import serializers
from .models import User


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
            "created_at",
            "updated_at",
        )


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
