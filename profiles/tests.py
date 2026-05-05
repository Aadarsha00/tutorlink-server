from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from accounts.models import User
from profiles.models import TeacherProfile, VerificationDocument
from profiles.verification import (
    TEACHER_REQUIRED_DOCUMENTS,
    sync_teacher_verification_status,
    teacher_documents_verified,
)


class TeacherVerificationStatusSyncTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="teacher@example.com",
            password="password",
            role="teacher",
            first_name="Test",
            last_name="Teacher",
            is_active=True,
            is_email_verified=True,
        )
        self.profile = TeacherProfile.objects.create(
            user=self.user,
            full_name="Test Teacher",
            phone="9800000000",
            education="Bachelor",
            experience_years=2,
            location="Kathmandu",
            address="Kathmandu",
            hourly_rate_min=500,
            hourly_rate_max=1000,
            bio="Experienced tutor",
        )

    def create_document(self, document_type, verified):
        return VerificationDocument.objects.create(
            teacher=self.profile,
            file=SimpleUploadedFile(
                f"{document_type}.pdf",
                b"test file",
                content_type="application/pdf",
            ),
            document_type=document_type,
            file_name=f"{document_type}.pdf",
            file_size=9,
            verified=verified,
        )

    def test_teacher_becomes_verified_when_all_required_documents_are_verified(self):
        for document_type in TEACHER_REQUIRED_DOCUMENTS:
            self.create_document(document_type, True)

        status = sync_teacher_verification_status(self.profile)
        self.profile.refresh_from_db()

        self.assertEqual(status, "verified")
        self.assertEqual(self.profile.verification_status, "verified")
        self.assertTrue(teacher_documents_verified(self.user))

    def test_teacher_becomes_verified_when_latest_submitted_documents_are_verified(self):
        for document_type in TEACHER_REQUIRED_DOCUMENTS[:-1]:
            self.create_document(document_type, True)

        status = sync_teacher_verification_status(self.profile)
        self.profile.refresh_from_db()

        self.assertEqual(status, "verified")
        self.assertEqual(self.profile.verification_status, "verified")
        self.assertFalse(teacher_documents_verified(self.user))

    def test_latest_required_document_controls_profile_status(self):
        for document_type in TEACHER_REQUIRED_DOCUMENTS:
            self.create_document(document_type, True)
        sync_teacher_verification_status(self.profile)

        self.create_document("academic", None)
        status = sync_teacher_verification_status(self.profile)
        self.profile.refresh_from_db()
        self.assertEqual(status, "pending")
        self.assertEqual(self.profile.verification_status, "pending")

        latest_academic = VerificationDocument.objects.filter(
            teacher=self.profile,
            document_type="academic",
        ).latest("uploaded_at")
        latest_academic.verified = False
        latest_academic.save(update_fields=["verified"])

        status = sync_teacher_verification_status(self.profile)
        self.profile.refresh_from_db()
        self.assertEqual(status, "rejected")
        self.assertEqual(self.profile.verification_status, "rejected")
