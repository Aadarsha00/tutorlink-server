# profiles/views.py
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import TeacherProfile, ParentProfile, Subject, Grade
from .serializers import (
    TeacherProfileSerializer,
    ParentProfileSerializer,
    SubjectSerializer,
    GradeSerializer,
)
from accounts.models import User


class TeacherProfileView(generics.GenericAPIView):
    """
    GET: Retrieve teacher profile
    POST: Create teacher profile
    PUT: Update teacher profile
    PATCH: Partially update teacher profile
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TeacherProfileSerializer

    def get_serializer_context(self):
        """Add request to serializer context"""
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def get(self, request):
        """Get the current user's teacher profile"""
        if request.user.role != "teacher":
            return Response(
                {"error": "Only teachers can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = TeacherProfile.objects.prefetch_related(
                "subjects", "grades", "availability_slots", "documents"
            ).get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except TeacherProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request):
        """Create a teacher profile"""
        if request.user.role != "teacher":
            return Response(
                {"error": "Only teachers can create a teacher profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if profile already exists
        if TeacherProfile.objects.filter(user=request.user).exists():
            return Response(
                {"error": "Profile already exists. Use PUT to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update teacher profile"""
        if request.user.role != "teacher":
            return Response(
                {"error": "Only teachers can update a teacher profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = TeacherProfile.objects.prefetch_related("subjects", "grades").get(
                user=request.user
            )
        except TeacherProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found. Use POST to create."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(profile, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """Partially update teacher profile"""
        if request.user.role != "teacher":
            return Response(
                {"error": "Only teachers can update a teacher profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = TeacherProfile.objects.prefetch_related("subjects", "grades").get(
                user=request.user
            )
        except TeacherProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found. Use POST to create."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ParentProfileView(generics.GenericAPIView):
    """
    GET: Retrieve parent profile
    POST: Create parent profile
    PUT: Update parent profile
    PATCH: Partially update parent profile
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ParentProfileSerializer

    def get(self, request):
        """Get the current user's parent profile"""
        if request.user.role != "parent":
            return Response(
                {"error": "Only parents can access this endpoint"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = ParentProfile.objects.get(user=request.user)
            serializer = self.get_serializer(profile)
            return Response(serializer.data)
        except ParentProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found"}, status=status.HTTP_404_NOT_FOUND
            )

    def post(self, request):
        """Create a parent profile"""
        if request.user.role != "parent":
            return Response(
                {"error": "Only parents can create a parent profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if profile already exists
        if ParentProfile.objects.filter(user=request.user).exists():
            return Response(
                {"error": "Profile already exists. Use PUT to update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request):
        """Update parent profile"""
        if request.user.role != "parent":
            return Response(
                {"error": "Only parents can update a parent profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = ParentProfile.objects.get(user=request.user)
        except ParentProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found. Use POST to create."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(profile, data=request.data, partial=False)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        """Partially update parent profile"""
        if request.user.role != "parent":
            return Response(
                {"error": "Only parents can update a parent profile"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = ParentProfile.objects.get(user=request.user)
        except ParentProfile.DoesNotExist:
            return Response(
                {"error": "Profile not found. Use POST to create."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_teacher_profile_by_id(request, teacher_id):
    """Get a teacher profile by user ID (public view)"""
    try:
        teacher = User.objects.get(id=teacher_id, role="teacher")
        profile = TeacherProfile.objects.prefetch_related(
            "subjects", "grades", "availability_slots", "documents"
        ).get(user=teacher)
        serializer = TeacherProfileSerializer(profile)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response(
            {"error": "Teacher not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except TeacherProfile.DoesNotExist:
        return Response(
            {"error": "Teacher profile not found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_parent_profile_by_id(request, parent_id):
    """Get a parent profile by user ID (public view)"""
    try:
        parent = User.objects.get(id=parent_id, role="parent")
        profile = ParentProfile.objects.get(user=parent)
        serializer = ParentProfileSerializer(profile)
        return Response(serializer.data)
    except User.DoesNotExist:
        return Response({"error": "Parent not found"}, status=status.HTTP_404_NOT_FOUND)
    except ParentProfile.DoesNotExist:
        return Response(
            {"error": "Parent profile not found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_teacher_profiles(request):
    """List all teacher profiles (with filtering)"""
    profiles = TeacherProfile.objects.select_related("user").prefetch_related(
        "subjects", "grades"
    )

    # Filter by verification status
    verification_status = request.query_params.get("verification_status")
    if verification_status:
        profiles = profiles.filter(verification_status=verification_status)

    # Filter by premium status
    is_premium = request.query_params.get("is_premium")
    if is_premium is not None:
        profiles = profiles.filter(is_premium=is_premium.lower() == "true")

    # Filter by location
    location = request.query_params.get("location")
    if location:
        profiles = profiles.filter(location__icontains=location)

    # Filter by subject (many-to-many)
    subject_id = request.query_params.get("subject_id")
    if subject_id:
        profiles = profiles.filter(subjects__id=subject_id)

    # Filter by grade (many-to-many)
    grade_id = request.query_params.get("grade_id")
    if grade_id:
        profiles = profiles.filter(grades__id=grade_id)

    # Search by name
    search = request.query_params.get("search")
    if search:
        profiles = profiles.filter(
            Q(full_name__icontains=search) | Q(user__email__icontains=search)
        )

    # Order by. Premium teachers stay ahead on the default list.
    order_by = request.query_params.get("order_by")
    if order_by:
        profiles = profiles.order_by(order_by).distinct()
    else:
        profiles = profiles.order_by("-is_premium", "-created_at").distinct()

    serializer = TeacherProfileSerializer(profiles, many=True)
    return Response(serializer.data)


# ============================================
# SUBJECT & GRADE VIEWS
# ============================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_subjects(request):
    """List all active subjects"""
    subjects = Subject.objects.filter(is_active=True).order_by("name")
    serializer = SubjectSerializer(subjects, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_grades(request):
    """List all active grades"""
    grades = Grade.objects.filter(is_active=True).order_by("order", "name")
    serializer = GradeSerializer(grades, many=True)
    return Response(serializer.data)


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from payments.models import PremiumSubscription
from payments.serializers import PremiumSubscriptionSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_premium_subscriptions(request):
    """Get all premium subscriptions (admin only)"""
    if request.user.role != "admin":
        return Response({"error": "Not authorized"}, status=403)

    subscriptions = (
        PremiumSubscription.objects.select_related("teacher")
        .all()
        .order_by("-created_at")
    )
    serializer = PremiumSubscriptionSerializer(subscriptions, many=True)
    return Response(serializer.data)
