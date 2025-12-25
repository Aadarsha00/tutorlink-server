# accounts/permissions.py

from rest_framework import permissions


class IsTeacher(permissions.BasePermission):
    """
    Permission check for teacher role only
    Usage: permission_classes = [IsAuthenticated, IsTeacher]
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "teacher"


class IsParent(permissions.BasePermission):
    """
    Permission check for parent role only
    Usage: permission_classes = [IsAuthenticated, IsParent]
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "parent"


class IsAdmin(permissions.BasePermission):
    """
    Permission check for admin role only
    Usage: permission_classes = [IsAuthenticated, IsAdmin]
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "admin"


class IsTeacherOrAdmin(permissions.BasePermission):
    """
    Permission check for teacher or admin roles
    Useful for endpoints that both teachers and admins can access
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            "teacher",
            "admin",
        ]


class IsParentOrAdmin(permissions.BasePermission):
    """
    Permission check for parent or admin roles
    Useful for endpoints that both parents and admins can access
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in [
            "parent",
            "admin",
        ]


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permission check for resource owner or admin
    Checks both view-level and object-level permissions
    """

    def has_permission(self, request, view):
        """Check if user is authenticated"""
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        """Check if user owns the object or is admin"""
        # Admin can access anything
        if request.user.role == "admin":
            return True

        # Check if user owns the object
        # Works for objects with 'user' attribute or User objects themselves
        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj == request.user


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Read permissions for everyone
    Write permissions only for owner or admin
    """

    def has_object_permission(self, request, view, obj):
        # Read permissions allowed for any authenticated user
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Write permissions only for owner or admin
        if request.user.role == "admin":
            return True

        if hasattr(obj, "user"):
            return obj.user == request.user

        return obj == request.user
