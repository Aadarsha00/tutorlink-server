import os

from django.conf import settings
from rest_framework import serializers
from django.utils import timezone
from accounts.models import User
from profiles.models import VerificationDocument
from profiles.serializers import TeacherProfileSerializer, VerificationDocumentSerializer
from profiles.verification import teacher_documents_verified
from .models import Job, JobApplication


class JobSerializer(serializers.ModelSerializer):
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    applications_count = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            "id",
            "created_by",
            "title",
            "school_name",
            "school_address",
            "school_contact_email",
            "school_contact_phone",
            "subject",
            "grade",
            "employment_type",
            "description",
            "requirements",
            "salary_min",
            "salary_max",
            "location",
            "deadline",
            "status",
            "applications_count",
            "has_applied",
            "created_at",
            "updated_at",
            "published_at",
            "closed_at",
        ]
        read_only_fields = [
            "id",
            "created_by",
            "applications_count",
            "has_applied",
            "created_at",
            "updated_at",
            "published_at",
            "closed_at",
        ]

    def get_applications_count(self, obj):
        return obj.applications.count()

    def get_has_applied(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        if request.user.role != "teacher":
            return False
        return obj.applications.filter(teacher=request.user).exists()

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None

        if user and user.role != "admin":
            raise serializers.ValidationError("Only admins can create or update jobs.")

        salary_min = attrs.get("salary_min", getattr(self.instance, "salary_min", None))
        salary_max = attrs.get("salary_max", getattr(self.instance, "salary_max", None))
        if salary_min is not None and salary_max is not None and salary_min > salary_max:
            raise serializers.ValidationError(
                {"salary_min": "Minimum salary cannot be greater than maximum salary."}
            )

        return attrs


class JobListSerializer(JobSerializer):
    class Meta(JobSerializer.Meta):
        fields = [
            "id",
            "created_by",
            "title",
            "school_name",
            "subject",
            "grade",
            "employment_type",
            "salary_min",
            "salary_max",
            "location",
            "deadline",
            "status",
            "applications_count",
            "has_applied",
            "created_at",
            "updated_at",
        ]


class JobApplicationSerializer(serializers.ModelSerializer):
    job = serializers.PrimaryKeyRelatedField(queryset=Job.objects.filter(status="open"))
    job_details = serializers.SerializerMethodField()
    teacher = serializers.PrimaryKeyRelatedField(read_only=True)
    teacher_profile = serializers.SerializerMethodField()
    cv_document = serializers.SerializerMethodField()
    cv_file = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = JobApplication
        fields = [
            "id",
            "job",
            "job_details",
            "teacher",
            "teacher_profile",
            "cv_document",
            "cv_file",
            "cover_letter",
            "status",
            "admin_notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "teacher",
            "teacher_profile",
            "cv_document",
            "status",
            "admin_notes",
            "created_at",
            "updated_at",
        ]

    def get_job_details(self, obj):
        job = obj.job
        return {
            "id": job.id,
            "title": job.title,
            "school_name": job.school_name,
            "subject": job.subject,
            "grade": job.grade,
            "employment_type": job.employment_type,
            "salary_min": float(job.salary_min) if job.salary_min is not None else None,
            "salary_max": float(job.salary_max) if job.salary_max is not None else None,
            "location": job.location,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        }

    def get_teacher_profile(self, obj):
        if hasattr(obj.teacher, "teacher_profile"):
            return TeacherProfileSerializer(
                obj.teacher.teacher_profile, context=self.context
            ).data
        return None

    def get_cv_document(self, obj):
        return VerificationDocumentSerializer(obj.cv_document, context=self.context).data

    def validate_cv_file(self, value):
        max_size = getattr(settings, "MAX_DOCUMENT_SIZE", 5 * 1024 * 1024)
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size exceeds {max_size / (1024 * 1024):.0f}MB limit"
            )

        ext = os.path.splitext(value.name)[1].lower()
        allowed_extensions = getattr(
            settings,
            "ALLOWED_DOCUMENT_EXTENSIONS",
            [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"],
        )
        if ext not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type {ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )

        return value

    def _latest_cv(self, user):
        if not hasattr(user, "teacher_profile"):
            return None
        return (
            VerificationDocument.objects.filter(
                teacher=user.teacher_profile,
                document_type="cv",
                verified=True,
            )
            .order_by("-uploaded_at")
            .first()
        )

    def _latest_profile_cv(self, user):
        if not hasattr(user, "teacher_profile"):
            return None
        return (
            VerificationDocument.objects.filter(
                teacher=user.teacher_profile,
                document_type="cv",
            )
            .order_by("-verified", "-uploaded_at")
            .first()
        )

    def _required_documents_except_cv_verified(self, user):
        if not hasattr(user, "teacher_profile"):
            return False
        required_document_types = ["citizenship_front", "citizenship_back", "academic"]
        for document_type in required_document_types:
            latest_document = (
                VerificationDocument.objects.filter(
                    teacher=user.teacher_profile,
                    document_type=document_type,
                )
                .order_by("-uploaded_at")
                .first()
            )
            if not latest_document or latest_document.verified is not True:
                return False
        return True

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        job = attrs.get("job")

        if user and user.role != "teacher":
            raise serializers.ValidationError("Only teachers can apply for jobs.")

        cv_file = attrs.get("cv_file")

        if user and cv_file:
            if not self._required_documents_except_cv_verified(user):
                raise serializers.ValidationError(
                    "Your identity and academic documents must be verified before you can apply for jobs."
                )
        elif user and not teacher_documents_verified(user):
            raise serializers.ValidationError(
                "Your documents must be verified before you can apply for jobs."
            )

        if job and job.status != "open":
            raise serializers.ValidationError("This job is not accepting applications.")

        if job and job.deadline and job.deadline < timezone.localdate():
            raise serializers.ValidationError("This job application deadline has passed.")

        if job and JobApplication.objects.filter(job=job, teacher=user).exists():
            raise serializers.ValidationError("You have already applied to this job.")

        if user and not cv_file and not self._latest_profile_cv(user):
            raise serializers.ValidationError(
                "Upload a CV for this application or add a CV to your teacher profile before applying."
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        cv_file = validated_data.pop("cv_file", None)
        validated_data["teacher"] = request.user
        if cv_file:
            validated_data["cv_document"] = VerificationDocument.objects.create(
                teacher=request.user.teacher_profile,
                file=cv_file,
                document_type="cv",
                file_name=cv_file.name,
                file_size=cv_file.size,
            )
        else:
            validated_data["cv_document"] = self._latest_profile_cv(request.user)
        return super().create(validated_data)


class JobApplicationListSerializer(JobApplicationSerializer):
    class Meta(JobApplicationSerializer.Meta):
        fields = [
            "id",
            "job",
            "job_details",
            "teacher",
            "teacher_profile",
            "cv_document",
            "cover_letter",
            "status",
            "admin_notes",
            "created_at",
            "updated_at",
        ]


class AdminJobApplicationUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobApplication
        fields = ["status", "admin_notes"]

    def validate_status(self, value):
        allowed = {choice[0] for choice in JobApplication.STATUS_CHOICES}
        if value not in allowed:
            raise serializers.ValidationError("Invalid application status.")
        return value
