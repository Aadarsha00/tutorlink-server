# accounts/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import User
from .serializers import UserSerializer
from .permissions import IsAdmin


class CustomUserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for managing users with role-based access

    Endpoints:
    - GET /users/ - List all users (admin only)
    - GET /users/{id}/ - Get specific user details
    - GET /users/teachers/ - List all teachers
    - GET /users/parents/ - List all parents (admin only)
    - GET /users/role/?role=teacher - Get users by role
    - GET /users/stats/ - Get user statistics (admin only)
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset based on user role
        - Admin: can see all users
        - Teacher: can see teachers and parents
        - Parent: can see teachers only
        """
        user = self.request.user

        # Admin can see all users
        if user.role == "admin":
            return User.objects.all()

        # Teachers can see parents and other teachers
        if user.role == "teacher":
            return User.objects.filter(role__in=["teacher", "parent"])

        # Parents can see teachers
        if user.role == "parent":
            return User.objects.filter(role="teacher")

        # Default: return only the current user
        return User.objects.filter(id=user.id)

    def get_permissions(self):
        """
        Set permissions based on action
        - list action: Admin only
        - Other actions: Authenticated users
        """
        if self.action == "list":
            permission_classes = [IsAuthenticated, IsAdmin]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def teachers(self, request):
        """
        Get all active teachers
        Accessible by all authenticated users

        GET /users/teachers/
        """
        teachers = User.objects.filter(role="teacher", is_active=True)
        serializer = self.get_serializer(teachers, many=True)
        return Response(serializer.data)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsAdmin]
    )
    def parents(self, request):
        """
        Get all active parents
        Admin only

        GET /users/parents/
        """
        parents = User.objects.filter(role="parent", is_active=True)
        serializer = self.get_serializer(parents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def role(self, request):
        """
        Get users by role with permission filtering

        GET /users/role/?role=teacher
        GET /users/role/?role=parent
        GET /users/role/?role=admin
        """
        role = request.query_params.get("role", None)

        if not role:
            return Response(
                {"error": "Role parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if role is valid
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if role not in valid_roles:
            return Response(
                {"error": f'Invalid role. Must be one of: {", ".join(valid_roles)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Apply role-based filtering
        if request.user.role == "admin":
            # Admin can see any role
            users = User.objects.filter(role=role, is_active=True)
        elif request.user.role == "teacher" and role in ["teacher", "parent"]:
            # Teachers can see teachers and parents
            users = User.objects.filter(role=role, is_active=True)
        elif request.user.role == "parent" and role == "teacher":
            # Parents can see teachers only
            users = User.objects.filter(role=role, is_active=True)
        else:
            return Response(
                {"error": "You do not have permission to view this role"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

    @action(
        detail=False, methods=["get"], permission_classes=[IsAuthenticated, IsAdmin]
    )
    def stats(self, request):
        """
        Get user statistics
        Admin only

        GET /users/stats/
        """
        stats = {
            "total_users": User.objects.count(),
            "active_users": User.objects.filter(is_active=True).count(),
            "teachers": {
                "total": User.objects.filter(role="teacher").count(),
                "active": User.objects.filter(role="teacher", is_active=True).count(),
            },
            "parents": {
                "total": User.objects.filter(role="parent").count(),
                "active": User.objects.filter(role="parent", is_active=True).count(),
            },
            "admins": {
                "total": User.objects.filter(role="admin").count(),
                "active": User.objects.filter(role="admin", is_active=True).count(),
            },
        }

        return Response(stats)
