# profiles/document_views.py

import os
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.conf import settings

from profiles.models import (
    TeacherProfile,
    ParentProfile,
    VerificationDocument,
    ParentVerificationDocument,
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


def validate_file(file):
    """Validate uploaded file size and extension"""
    max_size = getattr(settings, "MAX_DOCUMENT_SIZE", 5 * 1024 * 1024)
    if file.size > max_size:
        return False, f"File size exceeds {max_size / (1024*1024):.0f}MB limit"

    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = getattr(
        settings,
        "ALLOWED_DOCUMENT_EXTENSIONS",
        [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"],
    )

    if ext not in allowed_extensions:
        allowed_str = ", ".join(allowed_extensions)
        return False, f"File type {ext} not allowed. Allowed types: {allowed_str}"

    return True, None


# ==================== TEACHER DOCUMENT VIEWS ====================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_teacher_document(request):
    """Upload teacher verification document"""
    if request.user.role != "teacher":
        return Response(
            {"error": "Only teachers can upload teacher documents"},
            status=status.HTTP_403_FORBIDDEN,
        )

    file = request.FILES.get("file")
    document_type = request.data.get("document_type")

    if not file:
        return Response(
            {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not document_type:
        return Response(
            {"error": "document_type is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    valid_types = [
        "citizenship_front",
        "citizenship_back",
        "academic",
        "cv",
        "other",
    ]
    if document_type not in valid_types:
        return Response(
            {
                "error": f'Invalid document_type. Must be one of: {", ".join(valid_types)}'
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_valid, error_message = validate_file(file)
    if not is_valid:
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

    try:
        teacher_profile = request.user.teacher_profile
    except AttributeError:
        return Response(
            {"error": "Teacher profile not found. Please create your profile first."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        document = VerificationDocument.objects.create(
            teacher=teacher_profile,
            file=file,
            document_type=document_type,
            file_name=file.name,
            file_size=file.size,
        )
        sync_teacher_verification_status(teacher_profile)

        logger.info(
            f"✅ Document uploaded: ID={document.id}, Teacher={request.user.email}, "
            f"Type={document_type}, Size={file.size} bytes"
        )

        try:
            from notifications.services import DocumentNotificationService

            DocumentNotificationService.notify_document_uploaded(document, request.user)
        except (ImportError, Exception) as e:
            logger.warning(f"Failed to send upload notification: {e}")

        serializer = VerificationDocumentSerializer(
            document, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"❌ Failed to upload document: {e}", exc_info=True)
        return Response(
            {"error": f"Failed to upload document: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_teacher_documents(request):
    """List all documents uploaded by current teacher"""
    if request.user.role != "teacher":
        return Response(
            {"error": "Only teachers can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        teacher_profile = TeacherProfile.objects.get(user=request.user)
        documents = VerificationDocument.objects.filter(
            teacher=teacher_profile
        ).order_by("-uploaded_at")

        serializer = VerificationDocumentSerializer(
            documents, many=True, context={"request": request}
        )
        return Response(serializer.data)

    except TeacherProfile.DoesNotExist:
        return Response(
            {"error": "Teacher profile not found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_teacher_document(request, document_id):
    """Delete a teacher document"""
    try:
        document = VerificationDocument.objects.get(id=document_id)
    except VerificationDocument.DoesNotExist:
        return Response(
            {"error": "Document not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if document.teacher.user != request.user:
        return Response(
            {"error": "You don't have permission to delete this document"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if document.verified:
        return Response(
            {"error": "Cannot delete verified documents"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    document_type = document.document_type
    teacher_profile = document.teacher
    document.delete()
    sync_teacher_verification_status(teacher_profile)

    logger.info(
        f"🗑️ Document deleted: ID={document_id}, Teacher={request.user.email}, "
        f"Type={document_type}"
    )

    return Response(
        {"message": "Document deleted successfully"}, status=status.HTTP_204_NO_CONTENT
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_teacher_document(request, document_id):
    """Download a teacher document"""
    try:
        document = VerificationDocument.objects.get(id=document_id)
    except VerificationDocument.DoesNotExist:
        return Response(
            {"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND
        )

    is_owner = document.teacher.user == request.user
    is_admin = request.user.role == "admin"

    if not (is_owner or is_admin):
        return Response(
            {"error": "You don't have permission to download this document"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if document.file:
        file_url = request.build_absolute_uri(document.file.url)
        return Response(
            {
                "file_url": file_url,
                "file_name": document.file_name,
                "file_size": document.file_size,
            }
        )
    else:
        return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)


# ==================== PARENT DOCUMENT VIEWS ====================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_parent_document(request):
    """Upload parent verification document"""
    if request.user.role != "parent":
        return Response(
            {"error": "Only parents can upload parent documents"},
            status=status.HTTP_403_FORBIDDEN,
        )

    file = request.FILES.get("file")
    document_type = request.data.get("document_type")

    if not file:
        return Response(
            {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not document_type:
        return Response(
            {"error": "document_type is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    valid_types = [
        "citizenship_front",
        "citizenship_back",
        "id_card",
        "supporting_document",
    ]
    if document_type not in valid_types:
        return Response(
            {
                "error": f'Invalid document_type. Must be one of: {", ".join(valid_types)}'
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    is_valid, error_message = validate_file(file)
    if not is_valid:
        return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

    try:
        parent_profile = request.user.parent_profile
    except AttributeError:
        return Response(
            {"error": "Parent profile not found. Please create your profile first."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        document = ParentVerificationDocument.objects.create(
            parent=parent_profile,
            file=file,
            document_type=document_type,
            file_name=file.name,
            file_size=file.size,
        )
        sync_parent_verification_status(parent_profile)

        logger.info(
            f"✅ Parent document uploaded: ID={document.id}, Parent={request.user.email}, "
            f"Type={document_type}, Size={file.size} bytes"
        )

        try:
            from notifications.services import DocumentNotificationService

            DocumentNotificationService.notify_parent_document_uploaded(
                document, request.user
            )
        except (ImportError, Exception) as e:
            logger.warning(f"Failed to send upload notification: {e}")

        serializer = ParentVerificationDocumentSerializer(
            document, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"❌ Failed to upload parent document: {e}", exc_info=True)
        return Response(
            {"error": f"Failed to upload document: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_parent_documents(request):
    """List all documents uploaded by current parent"""
    if request.user.role != "parent":
        return Response(
            {"error": "Only parents can access this endpoint"},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        parent_profile = ParentProfile.objects.get(user=request.user)
        documents = ParentVerificationDocument.objects.filter(
            parent=parent_profile
        ).order_by("-uploaded_at")

        serializer = ParentVerificationDocumentSerializer(
            documents, many=True, context={"request": request}
        )
        return Response(serializer.data)

    except ParentProfile.DoesNotExist:
        return Response(
            {"error": "Parent profile not found"}, status=status.HTTP_404_NOT_FOUND
        )


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_parent_document(request, document_id):
    """Delete a parent document"""
    try:
        document = ParentVerificationDocument.objects.get(id=document_id)
    except ParentVerificationDocument.DoesNotExist:
        return Response(
            {"error": "Document not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    if document.parent.user != request.user:
        return Response(
            {"error": "You don't have permission to delete this document"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if document.verified:
        return Response(
            {"error": "Cannot delete verified documents"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    document_type = document.document_type
    parent_profile = document.parent
    document.delete()
    sync_parent_verification_status(parent_profile)

    logger.info(
        f"🗑️ Parent document deleted: ID={document_id}, Parent={request.user.email}, "
        f"Type={document_type}"
    )

    return Response(
        {"message": "Document deleted successfully"}, status=status.HTTP_204_NO_CONTENT
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_parent_document(request, document_id):
    """Download a parent document"""
    try:
        document = ParentVerificationDocument.objects.get(id=document_id)
    except ParentVerificationDocument.DoesNotExist:
        return Response(
            {"error": "Document not found"}, status=status.HTTP_404_NOT_FOUND
        )

    is_owner = document.parent.user == request.user
    is_admin = request.user.role == "admin"

    if not (is_owner or is_admin):
        return Response(
            {"error": "You don't have permission to download this document"},
            status=status.HTTP_403_FORBIDDEN,
        )

    if document.file:
        file_url = request.build_absolute_uri(document.file.url)
        return Response(
            {
                "file_url": file_url,
                "file_name": document.file_name,
                "file_size": document.file_size,
            }
        )
    else:
        return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)


# ==================== PROFILE COMPLETION CHECK ====================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_profile_completion(request):
    """Check if user's profile is complete with all required info and documents"""
    user = request.user

    if user.role == "teacher":
        try:
            profile = TeacherProfile.objects.get(user=user)
            documents = VerificationDocument.objects.filter(teacher=profile)

            required_fields = {
                "full_name": bool(profile.full_name),
                "phone": bool(profile.phone),
                "education": bool(profile.education),
                "experience_years": profile.experience_years >= 0,
                "subjects": profile.subjects.exists(),
                "grades": profile.grades.exists(),
                "location": bool(profile.location),
                "address": bool(profile.address),
                "hourly_rate_min": profile.hourly_rate_min > 0,
                "hourly_rate_max": profile.hourly_rate_max > 0,
                "bio": bool(profile.bio),
            }

            has_citizenship_front = documents.filter(
                document_type="citizenship_front"
            ).exists()
            has_citizenship_back = documents.filter(
                document_type="citizenship_back"
            ).exists()
            has_academic = documents.filter(document_type="academic").exists()
            has_cv = documents.filter(document_type="cv").exists()

            missing_fields = [
                field for field, complete in required_fields.items() if not complete
            ]
            missing_documents = []
            if not has_citizenship_front:
                missing_documents.append("citizenship_front")
            if not has_citizenship_back:
                missing_documents.append("citizenship_back")
            if not has_academic:
                missing_documents.append("academic")
            if not has_cv:
                missing_documents.append("cv")

            is_complete = len(missing_fields) == 0 and len(missing_documents) == 0

            total_items = len(required_fields) + 4
            completed_fields = len([v for v in required_fields.values() if v])
            completed_documents = 4 - len(missing_documents)
            total_completed = completed_fields + completed_documents
            completion_percentage = round((total_completed / total_items) * 100)

            return Response(
                {
                    "is_complete": is_complete,
                    "profile_exists": True,
                    "missing_fields": missing_fields,
                    "missing_documents": missing_documents,
                    "completion_percentage": completion_percentage,
                    "has_documents": {
                        "citizenship_front": has_citizenship_front,
                        "citizenship_back": has_citizenship_back,
                        "academic": has_academic,
                        "cv": has_cv,
                    },
                    "document_count": documents.count(),
                }
            )

        except TeacherProfile.DoesNotExist:
            return Response(
                {
                    "is_complete": False,
                    "profile_exists": False,
                    "message": "Teacher profile not created",
                    "completion_percentage": 0,
                }
            )

    elif user.role == "parent":
        try:
            profile = ParentProfile.objects.get(user=user)
            documents = ParentVerificationDocument.objects.filter(parent=profile)

            required_fields = {
                "full_name": bool(profile.full_name),
                "phone": bool(profile.phone),
                "location": bool(profile.location),
                "address": bool(profile.address),
            }

            has_citizenship_front = documents.filter(
                document_type="citizenship_front", verified=True
            ).exists()
            has_citizenship_back = documents.filter(
                document_type="citizenship_back", verified=True
            ).exists()
            has_id_card = documents.filter(
                document_type="id_card", verified=True
            ).exists()
            has_supporting_document = documents.filter(
                document_type="supporting_document", verified=True
            ).exists()

            missing_fields = [
                field for field, complete in required_fields.items() if not complete
            ]
            # Both citizenship_front and citizenship_back are required; ID and supporting docs are optional
            missing_documents = []
            if not has_citizenship_front:
                missing_documents.append("citizenship_front")
            if not has_citizenship_back:
                missing_documents.append("citizenship_back")

            is_complete = len(missing_fields) == 0 and len(missing_documents) == 0

            total_items = len(required_fields) + 2
            completed_fields = len([v for v in required_fields.values() if v])
            completed_documents = sum([has_citizenship_front, has_citizenship_back])
            total_completed = completed_fields + completed_documents
            completion_percentage = round((total_completed / total_items) * 100)

            return Response(
                {
                    "is_complete": is_complete,
                    "profile_exists": True,
                    "missing_fields": missing_fields,
                    "missing_documents": missing_documents,
                    "completion_percentage": completion_percentage,
                    "has_documents": {
                        "citizenship_front": has_citizenship_front,
                        "citizenship_back": has_citizenship_back,
                        "id_card": has_id_card,
                        "supporting_document": has_supporting_document,
                    },
                    "document_count": documents.count(),
                }
            )

        except ParentProfile.DoesNotExist:
            return Response(
                {
                    "is_complete": False,
                    "profile_exists": False,
                    "message": "Parent profile not created",
                    "completion_percentage": 0,
                }
            )

    return Response(
        {"message": "Invalid user role"}, status=status.HTTP_400_BAD_REQUEST
    )
