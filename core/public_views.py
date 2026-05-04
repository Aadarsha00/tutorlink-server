import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Avg, Count, F, Q
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts.models import User
from profiles.models import Rating, Subject, TeacherProfile
from profiles.serializers import SubjectSerializer, TeacherProfileSerializer

logger = logging.getLogger(__name__)


class ContactMessageSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    email = serializers.EmailField()
    subject = serializers.CharField(max_length=160)
    message = serializers.CharField(max_length=3000)


@api_view(["GET"])
@permission_classes([AllowAny])
def landing_data(request):
    teachers = User.objects.filter(role="teacher", is_active=True)
    parents = User.objects.filter(role="parent", is_active=True)
    subjects = Subject.objects.filter(is_active=True).order_by("name")

    featured_tutors = (
        TeacherProfile.objects.select_related("user")
        .prefetch_related("subjects", "grades")
        .filter(user__is_active=True, verification_status="verified")
        .annotate(
            average_score=Avg(
                "user__ratings_received__score",
                filter=Q(user__ratings_received__rater_type="parent"),
            ),
            rating_count=Count(
                "user__ratings_received",
                filter=Q(user__ratings_received__rater_type="parent"),
            ),
        )
        .order_by(
            F("average_score").desc(nulls_last=True),
            "-is_premium",
            "-rating_count",
            "-created_at",
        )[:4]
    )

    hero_tutors = (
        TeacherProfile.objects.select_related("user")
        .prefetch_related("subjects", "grades")
        .filter(user__is_active=True)
        .filter(user__profile_picture_verified=True)
        .exclude(user__profile_picture="")
        .order_by("-is_premium", "verification_status", "-created_at")[:3]
    )

    average_rating = (
        Rating.objects.filter(
            rater_type="parent",
            ratee__role="teacher",
            ratee__is_active=True,
        ).aggregate(value=Avg("score"))["value"]
        or 0
    )

    return Response(
        {
            "stats": {
                "teachers": teachers.count(),
                "parents": parents.count(),
                "subjects": subjects.count(),
                "average_rating": round(float(average_rating), 1),
            },
            "subjects": SubjectSerializer(subjects[:8], many=True).data,
            "featured_tutors": TeacherProfileSerializer(
                featured_tutors,
                many=True,
                context={"request": request},
            ).data,
            "hero_tutors": TeacherProfileSerializer(
                hero_tutors,
                many=True,
                context={"request": request},
            ).data,
        }
    )


def _profile_picture_url(user, request):
    if not getattr(user, "profile_picture", None):
        return None
    if user.profile_picture_verified is not True:
        return None
    if request:
        return request.build_absolute_uri(user.profile_picture.url)
    return user.profile_picture.url


def _serialize_testimonial(rating, request):
    return {
        "id": rating.id,
        "name": rating.rater.get_full_name() or rating.rater.email,
        "grade": rating.gig.grade if rating.gig else "",
        "subject": rating.gig.subject if rating.gig else "",
        "image": _profile_picture_url(rating.rater, request),
        "rating": rating.score,
        "quote": rating.review,
        "improvement": f"{rating.score}/5",
        "tutorName": rating.ratee.get_full_name() or rating.ratee.email,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def testimonials(request):
    ratings = (
        Rating.objects.select_related("rater", "ratee", "gig")
        .filter(rater_type="parent", score__gte=4)
        .exclude(review="")
        .order_by("-score", "-created_at")[:6]
    )

    return Response(
        {"results": [_serialize_testimonial(rating, request) for rating in ratings]}
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def tutors(request):
    profiles = (
        TeacherProfile.objects.select_related("user")
        .prefetch_related("subjects", "grades")
        .filter(user__is_active=True, verification_status="verified")
    )

    search = request.query_params.get("search")
    if search:
        profiles = profiles.filter(
            Q(full_name__icontains=search)
            | Q(education__icontains=search)
            | Q(bio__icontains=search)
            | Q(subjects__name__icontains=search)
        )

    subject_id = request.query_params.get("subject_id")
    if subject_id:
        profiles = profiles.filter(subjects__id=subject_id)

    location = request.query_params.get("location")
    if location:
        profiles = profiles.filter(location__icontains=location)

    is_premium = request.query_params.get("is_premium")
    if is_premium is not None:
        profiles = profiles.filter(is_premium=is_premium.lower() == "true")

    min_rating = request.query_params.get("min_rating")
    if min_rating:
        try:
            profiles = [
                profile
                for profile in profiles.distinct()
                if float(profile.average_rating) >= float(min_rating)
            ]
        except ValueError:
            profiles = profiles.distinct()
    else:
        profiles = profiles.distinct().order_by(
            "-is_premium", "-created_at"
        )

    if not isinstance(profiles, list):
        profiles = list(profiles)

    locations = (
        TeacherProfile.objects.filter(
            user__is_active=True,
            verification_status="verified",
        )
        .exclude(location="")
        .order_by("location")
        .values_list("location", flat=True)
        .distinct()
    )
    subjects = (
        Subject.objects.filter(
            is_active=True,
            teachers__user__is_active=True,
            teachers__verification_status="verified",
        )
        .distinct()
        .order_by("name")
    )

    return Response(
        {
            "count": len(profiles),
            "results": TeacherProfileSerializer(
                profiles,
                many=True,
                context={"request": request},
            ).data,
            "subjects": SubjectSerializer(subjects, many=True).data,
            "locations": list(locations),
        }
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def contact_message(request):
    serializer = ContactMessageSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    body = (
        f"Name: {data['name']}\n"
        f"Email: {data['email']}\n"
        f"Subject: {data['subject']}\n\n"
        f"{data['message']}"
    )

    try:
        send_mail(
            subject=f"TutorLink contact: {data['subject']}",
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[getattr(settings, "DEFAULT_FROM_EMAIL", data["email"])],
            fail_silently=True,
        )
    except Exception:
        logger.exception("Contact email delivery failed")

    logger.info("Contact message received from %s <%s>", data["name"], data["email"])
    return Response(
        {"message": "Thanks for reaching out. We will get back to you soon."},
        status=status.HTTP_201_CREATED,
    )
