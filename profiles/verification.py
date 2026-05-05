from profiles.models import (
    ParentProfile,
    ParentVerificationDocument,
    TeacherProfile,
    VerificationDocument,
)

TEACHER_REQUIRED_DOCUMENTS = (
    "citizenship_front",
    "citizenship_back",
    "academic",
    "cv",
)
# Parents need both citizenship front and back verified; ID and supporting docs are optional
PARENT_REQUIRED_DOCUMENTS = ("citizenship_front", "citizenship_back")


def _latest_documents_by_type(documents):
    latest = {}
    for document in documents.order_by("-uploaded_at"):
        latest.setdefault(document.document_type, document)
    return latest


def teacher_documents_verified(user):
    try:
        profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return False

    documents = _latest_documents_by_type(
        VerificationDocument.objects.filter(teacher=profile)
    )
    return all(
        documents.get(document_type)
        and documents[document_type].verified is True
        for document_type in TEACHER_REQUIRED_DOCUMENTS
    )


def teacher_document_verification_status(profile):
    documents = _latest_documents_by_type(
        VerificationDocument.objects.filter(teacher=profile).exclude(
            document_type="other"
        )
    )

    latest_documents = list(documents.values())

    if latest_documents and all(
        document.verified is True for document in latest_documents
    ):
        return "verified"

    if any(document.verified is False for document in latest_documents):
        return "rejected"

    return "pending"


def sync_teacher_verification_status(profile):
    status = teacher_document_verification_status(profile)
    if profile.verification_status != status:
        profile.verification_status = status
        profile.save(update_fields=["verification_status", "updated_at"])
    return status


def parent_documents_verified(user):
    try:
        profile = ParentProfile.objects.get(user=user)
    except ParentProfile.DoesNotExist:
        return False

    documents = _latest_documents_by_type(
        ParentVerificationDocument.objects.filter(parent=profile)
    )
    # Both citizenship_front and citizenship_back are required
    citizenship_front = documents.get("citizenship_front")
    citizenship_back = documents.get("citizenship_back")
    return (
        citizenship_front and citizenship_front.verified is True
        and citizenship_back and citizenship_back.verified is True
    )


def parent_document_verification_status(profile):
    documents = _latest_documents_by_type(
        ParentVerificationDocument.objects.filter(parent=profile)
    )

    required_documents = [
        documents.get(document_type) for document_type in PARENT_REQUIRED_DOCUMENTS
    ]

    if all(document and document.verified is True for document in required_documents):
        return "verified"

    if any(document and document.verified is False for document in required_documents):
        return "rejected"

    return "pending"


def sync_parent_verification_status(profile):
    status = parent_document_verification_status(profile)
    if profile.verification_status != status:
        profile.verification_status = status
        profile.save(update_fields=["verification_status", "updated_at"])
    return status
