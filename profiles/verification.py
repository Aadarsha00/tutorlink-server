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
    "experience",
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
