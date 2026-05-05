# profiles/admin_views.py

import os

from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from profiles.models import (
    VerificationDocument,
    ParentVerificationDocument,
    TeacherProfile,
    ParentProfile,
)
from profiles.serializers import (
    VerificationDocumentSerializer,
    ParentVerificationDocumentSerializer,
)
from profiles.verification import (
    sync_parent_verification_status,
    sync_teacher_verification_status,
)
import logging

logger = logging.getLogger(__name__)


def _profile_photo_url(profile, request):
    if not profile.kyc_photo:
        return None
    return request.build_absolute_uri(profile.kyc_photo.url)


def _profile_photo_status(profile):
    if profile.kyc_photo_verified:
        return True
    if profile.kyc_photo_rejection_reason:
        return False
    return None


def _profile_photo_file_size(profile):
    try:
        return profile.kyc_photo.size if profile.kyc_photo else 0
    except OSError:
        return 0


def _serialize_profile_photo(profile, user_type, request):
    user = profile.user
    file_url = _profile_photo_url(profile, request)
    return {
        "id": profile.id,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.get_full_name(),
            "role": user.role,
            "profile_picture": file_url,
        },
        "document_type": "profile_picture",
        "file_name": os.path.basename(profile.kyc_photo.name) if profile.kyc_photo else "",
        "file_url": file_url,
        "file_size": _profile_photo_file_size(profile),
        "uploaded_at": profile.updated_at,
        "verified": _profile_photo_status(profile),
        "verified_at": None,
        "verified_by": None,
        "rejection_reason": profile.kyc_photo_rejection_reason,
        "notes": "",
        "user_type": user_type,
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def list_profile_photos(request):
    status_filter = request.query_params.get("status")

    profiles = [
        *[
            _serialize_profile_photo(profile, "teacher", request)
            for profile in TeacherProfile.objects.select_related("user")
            .exclude(kyc_photo="")
            .exclude(kyc_photo__isnull=True)
        ],
        *[
            _serialize_profile_photo(profile, "parent", request)
            for profile in ParentProfile.objects.select_related("user")
            .exclude(kyc_photo="")
            .exclude(kyc_photo__isnull=True)
        ],
    ]

    if status_filter in {"pending", "verified", "rejected"}:
        profiles = [
            profile
            for profile in profiles
            if (
                (status_filter == "pending" and profile["verified"] is None)
                or (status_filter == "verified" and profile["verified"] is True)
                or (status_filter == "rejected" and profile["verified"] is False)
            )
        ]

    profiles.sort(key=lambda profile: profile["uploaded_at"], reverse=True)
    return Response(
        {
            "count": len(profiles),
            "next": None,
            "previous": None,
            "results": profiles,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsAdminUser])
def verify_profile_photo(request, user_type, profile_id):
    if user_type == "teacher":
        model = TeacherProfile
    elif user_type == "parent":
        model = ParentProfile
    else:
        return Response(
            {"error": "user_type must be teacher or parent"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        profile = model.objects.select_related("user").get(id=profile_id)
    except model.DoesNotExist:
        return Response(
            {"error": "Profile photo not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    verified = request.data.get("verified")
    rejection_reason = request.data.get("rejection_reason", "")

    if verified is None:
        return Response(
            {"error": "verified field is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if verified is False and not rejection_reason:
        return Response(
            {"error": "rejection_reason is required when rejecting profile pictures"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    profile.kyc_photo_verified = verified
    profile.kyc_photo_rejection_reason = "" if verified else rejection_reason
    profile.save(
        update_fields=[
            "kyc_photo_verified",
            "kyc_photo_rejection_reason",
            "updated_at",
        ]
    )

    if verified:
        profile.user.profile_picture = profile.kyc_photo.name
        profile.user.profile_picture_verified = True
        profile.user.profile_picture_rejection_reason = ""
        profile.user.profile_picture_verified_at = timezone.now()
        profile.user.profile_picture_verified_by = request.user
        profile.user.save(
            update_fields=[
                "profile_picture",
                "profile_picture_verified",
                "profile_picture_rejection_reason",
                "profile_picture_verified_at",
                "profile_picture_verified_by",
                "updated_at",
            ]
        )

    return Response(_serialize_profile_photo(profile, user_type, request))


class AdminTeacherDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only viewset for teacher document verification

    Endpoints:
    - GET    /api/profiles/admin/teacher-documents/          - List all teacher documents
    - GET    /api/profiles/admin/teacher-documents/{id}/     - Get single document
    - POST   /api/profiles/admin/teacher-documents/{id}/verify/ - Verify/reject document
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = VerificationDocumentSerializer
    queryset = VerificationDocument.objects.all()

    def get_queryset(self):
        """Get all teacher documents with related data"""
        queryset = VerificationDocument.objects.select_related(
            "teacher__user", "verified_by"
        ).order_by("-uploaded_at")

        status_filter = self.request.query_params.get("status")
        if status_filter == "pending":
            queryset = queryset.filter(verified__isnull=True)
        elif status_filter == "verified":
            queryset = queryset.filter(verified=True)
        elif status_filter == "rejected":
            queryset = queryset.filter(verified=False)

        return queryset

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """
        Verify or reject a teacher document

        POST /api/profiles/admin/teacher-documents/{id}/verify/
        Body: {
            "verified": true/false,
            "notes": "Optional notes",
            "rejection_reason": "Required if rejected"
        }
        """
        document = self.get_object()
        verified = request.data.get("verified")
        notes = request.data.get("notes", "")
        rejection_reason = request.data.get("rejection_reason", "")

        if verified is None:
            return Response(
                {"error": "verified field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verified is False and not rejection_reason:
            return Response(
                {"error": "rejection_reason is required when rejecting documents"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document.verified = verified
        document.verified_at = timezone.now()
        document.verified_by = request.user
        document.notes = notes

        if verified:
            document.rejection_reason = ""
        else:
            document.rejection_reason = rejection_reason

        document.save()
        sync_teacher_verification_status(document.teacher)

        teacher = document.teacher.user

        try:
            from notifications.services import DocumentNotificationService

            if verified:
                DocumentNotificationService.notify_document_verified(document, teacher)
                logger.info(
                    f"✅ Teacher document {document.id} verified for {teacher.email}"
                )
            else:
                DocumentNotificationService.notify_document_rejected(
                    document, teacher, rejection_reason
                )
                logger.info(
                    f"❌ Teacher document {document.id} rejected for {teacher.email}"
                )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

        serializer = self.get_serializer(document)
        return Response(serializer.data)


class AdminParentDocumentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Admin-only viewset for parent document verification

    Endpoints:
    - GET    /api/profiles/admin/parent-documents/          - List all parent documents
    - GET    /api/profiles/admin/parent-documents/{id}/     - Get single document
    - POST   /api/profiles/admin/parent-documents/{id}/verify/ - Verify/reject document
    """

    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = ParentVerificationDocumentSerializer
    queryset = ParentVerificationDocument.objects.all()

    def get_queryset(self):
        """Get all parent documents with related data"""
        queryset = ParentVerificationDocument.objects.select_related(
            "parent__user", "verified_by"
        ).order_by("-uploaded_at")

        status_filter = self.request.query_params.get("status")
        if status_filter == "pending":
            queryset = queryset.filter(verified__isnull=True)
        elif status_filter == "verified":
            queryset = queryset.filter(verified=True)
        elif status_filter == "rejected":
            queryset = queryset.filter(verified=False)

        return queryset

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        """
        Verify or reject a parent document

        POST /api/profiles/admin/parent-documents/{id}/verify/
        Body: {
            "verified": true/false,
            "notes": "Optional notes",
            "rejection_reason": "Required if rejected"
        }
        """
        document = self.get_object()
        verified = request.data.get("verified")
        notes = request.data.get("notes", "")
        rejection_reason = request.data.get("rejection_reason", "")

        if verified is None:
            return Response(
                {"error": "verified field is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if verified is False and not rejection_reason:
            return Response(
                {"error": "rejection_reason is required when rejecting documents"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        document.verified = verified
        document.verified_at = timezone.now()
        document.verified_by = request.user
        document.notes = notes

        if verified:
            document.rejection_reason = ""
        else:
            document.rejection_reason = rejection_reason

        document.save()
        sync_parent_verification_status(document.parent)

        parent = document.parent.user

        try:
            from notifications.services import DocumentNotificationService

            if verified:
                DocumentNotificationService.notify_parent_document_verified(
                    document, parent
                )
                logger.info(
                    f"✅ Parent document {document.id} verified for {parent.email}"
                )
            else:
                DocumentNotificationService.notify_parent_document_rejected(
                    document, parent, rejection_reason
                )
                logger.info(
                    f"❌ Parent document {document.id} rejected for {parent.email}"
                )
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")

        serializer = self.get_serializer(document)
        return Response(serializer.data)
