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

    class Meta:
        model = JobApplication
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

    def validate(self, attrs):
        request = self.context.get("request")
        user = request.user if request else None
        job = attrs.get("job")

        if user and user.role != "teacher":
            raise serializers.ValidationError("Only teachers can apply for jobs.")

        if user and not teacher_documents_verified(user):
            raise serializers.ValidationError(
                "Your documents must be verified before you can apply for jobs."
            )

        if job and job.status != "open":
            raise serializers.ValidationError("This job is not accepting applications.")

        if job and job.deadline and job.deadline < timezone.localdate():
            raise serializers.ValidationError("This job application deadline has passed.")

        if job and JobApplication.objects.filter(job=job, teacher=user).exists():
            raise serializers.ValidationError("You have already applied to this job.")

        if user and not self._latest_cv(user):
            raise serializers.ValidationError(
                "A verified CV must be uploaded in your teacher profile before applying."
            )

        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        validated_data["teacher"] = request.user
        validated_data["cv_document"] = self._latest_cv(request.user)
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
