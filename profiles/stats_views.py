# profiles/stats_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Sum, Avg, Count, Q, F
from django.db.models.functions import TruncMonth, TruncWeek, TruncDay
from django.utils import timezone
from datetime import timedelta, datetime

from accounts.models import User
from applications.models import Application
from gigs.models import Gig
from profiles.models import Rating
from payments.models import PremiumSubscription, GigPayment
from payments.serializers import PremiumSubscriptionSerializer


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teacher_stats(request):
    """Get comprehensive statistics for teacher dashboard with chart data"""
    if request.user.role != "teacher":
        return Response({"error": "Not authorized"}, status=403)

    # ============ PARSE FILTER PARAMETERS ============
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    now = timezone.now()

    if date_from and date_to:
        try:
            start_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
        except (ValueError, AttributeError):
            start_date = now - timedelta(days=180)
            end_date = now
    else:
        start_date = now - timedelta(days=180)
        end_date = now

    thirty_days_ago = now - timedelta(days=30)

    # ============ APPLICATION METRICS ============
    applications = Application.objects.filter(teacher=request.user)

    total_applications = applications.count()
    pending_applications = applications.filter(status="pending").count()
    selected_applications = applications.filter(status="selected").count()
    accepted_applications = applications.filter(status="accepted").count()
    rejected_applications = applications.filter(status="rejected").count()
    withdrawn_applications = applications.filter(status="withdrawn").count()

    # Calculate acceptance rate
    selected = applications.filter(
        status__in=["selected", "accepted", "rejected"]
    ).count()
    acceptance_rate = round(
        (accepted_applications / selected * 100) if selected > 0 else 0, 1
    )

    # Applications by status
    applications_by_status = applications.values("status").annotate(count=Count("id"))
    applications_by_status_data = {
        item["status"]: item["count"] for item in applications_by_status
    }

    # Application trends over time
    application_trends = (
        applications.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    application_trends_data = [
        {"month": item["month"].strftime("%Y-%m"), "count": item["count"]}
        for item in application_trends
    ]

    # Success rate over time (selected + accepted vs total)
    monthly_success = (
        applications.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total=Count("id"),
            successful=Count("id", filter=Q(status__in=["selected", "accepted"])),
        )
        .order_by("month")
    )

    success_rate_data = [
        {
            "month": item["month"].strftime("%Y-%m"),
            "success_rate": round(
                (item["successful"] / item["total"] * 100) if item["total"] > 0 else 0,
                1,
            ),
            "total_applications": item["total"],
            "successful_applications": item["successful"],
        }
        for item in monthly_success
    ]

    # Recent application activity (last 30 days)
    recent_applications = applications.filter(created_at__gte=thirty_days_ago).count()

    # Applications by subject
    applications_by_subject = (
        applications.values("gig__subject")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    applications_by_subject_data = [
        {"subject": item["gig__subject"], "count": item["count"]}
        for item in applications_by_subject
    ]

    # Applications by grade
    applications_by_grade = (
        applications.values("gig__grade")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    applications_by_grade_data = [
        {"grade": item["gig__grade"], "count": item["count"]}
        for item in applications_by_grade
    ]

    # ============ GIG METRICS ============
    # All gigs where teacher is involved (hired or selected)
    hired_gigs = Gig.objects.filter(hired_teacher=request.user)
    selected_gigs = Gig.objects.filter(selected_teacher=request.user)

    active_gigs = hired_gigs.filter(status="active").count()
    completed_gigs = hired_gigs.filter(status="completed").count()
    total_hired_gigs = hired_gigs.count()

    # Gigs by status
    gigs_by_status = hired_gigs.values("status").annotate(count=Count("id"))
    gigs_by_status_data = {item["status"]: item["count"] for item in gigs_by_status}

    # Gig completion trends
    gig_completion_trends = (
        hired_gigs.filter(
            closed_at__gte=start_date, closed_at__lte=end_date, status="completed"
        )
        .annotate(month=TruncMonth("closed_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    gig_completion_data = [
        {"month": item["month"].strftime("%Y-%m"), "count": item["count"]}
        for item in gig_completion_trends
    ]

    # Gigs by subject (completed or active)
    gigs_by_subject = (
        hired_gigs.filter(status__in=["active", "completed"])
        .values("subject")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    gigs_by_subject_data = [
        {"subject": item["subject"], "count": item["count"]} for item in gigs_by_subject
    ]

    # Gigs by grade
    gigs_by_grade = (
        hired_gigs.filter(status__in=["active", "completed"])
        .values("grade")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    gigs_by_grade_data = [
        {"grade": item["grade"], "count": item["count"]} for item in gigs_by_grade
    ]

    # Average gig duration
    avg_gig_duration = (
        hired_gigs.filter(status__in=["completed", "active"]).aggregate(
            avg=Avg("duration_weeks")
        )["avg"]
        or 0
    )

    # ============ EARNINGS METRICS ============
    payments = GigPayment.objects.filter(teacher=request.user, status="completed")

    # Total earnings (amount - platform_fee)
    total_earned = sum(
        [float(payment.amount - payment.platform_fee) for payment in payments]
    )

    # Average earnings per gig
    avg_earnings_per_gig = (
        total_earned / payments.count() if payments.count() > 0 else 0
    )

    # Earnings over time
    earnings_trends = (
        payments.filter(paid_at__gte=start_date, paid_at__lte=end_date)
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(
            total_amount=Sum("amount"),
            platform_fees=Sum("platform_fee"),
            count=Count("id"),
        )
        .order_by("month")
    )

    earnings_trends_data = [
        {
            "month": item["month"].strftime("%Y-%m"),
            "gross_earnings": float(item["total_amount"] or 0),
            "platform_fees": float(item["platform_fees"] or 0),
            "net_earnings": float(
                (item["total_amount"] or 0) - (item["platform_fees"] or 0)
            ),
            "gig_count": item["count"],
        }
        for item in earnings_trends
    ]

    # Earnings by subject
    earnings_by_subject = (
        payments.values("gig__subject")
        .annotate(total=Sum(F("amount") - F("platform_fee")), count=Count("id"))
        .order_by("-total")[:10]
    )

    earnings_by_subject_data = [
        {
            "subject": item["gig__subject"],
            "earnings": float(item["total"] or 0),
            "gig_count": item["count"],
        }
        for item in earnings_by_subject
    ]

    # Recent earnings (last 30 days)
    recent_earnings = sum(
        [
            float(payment.amount - payment.platform_fee)
            for payment in payments.filter(paid_at__gte=thirty_days_ago)
        ]
    )

    # ============ RATING METRICS ============
    ratings = Rating.objects.filter(ratee=request.user, rater_type="parent")
    average_rating = ratings.aggregate(avg=Avg("score"))["avg"] or 0
    total_reviews = ratings.count()

    # Rating distribution
    rating_distribution = (
        ratings.values("score").annotate(count=Count("id")).order_by("score")
    )

    rating_distribution_data = {str(i): 0 for i in range(1, 6)}
    for item in rating_distribution:
        rating_distribution_data[str(item["score"])] = item["count"]

    # Ratings over time
    rating_trends = (
        ratings.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"), avg_score=Avg("score"))
        .order_by("month")
    )

    rating_trends_data = [
        {
            "month": item["month"].strftime("%Y-%m"),
            "total_ratings": item["count"],
            "average_rating": round(item["avg_score"], 2),
        }
        for item in rating_trends
    ]

    # Recent ratings (last 30 days)
    recent_ratings = ratings.filter(created_at__gte=thirty_days_ago).count()

    # ============ PREMIUM STATUS ============
    from profiles.models import TeacherProfile

    try:
        teacher_profile = TeacherProfile.objects.get(user=request.user)
        is_premium = teacher_profile.is_premium
        premium_expires_at = teacher_profile.premium_expires_at
    except TeacherProfile.DoesNotExist:
        is_premium = False
        premium_expires_at = None

    active_subscription = PremiumSubscription.objects.filter(
        teacher=request.user, status="active"
    ).first()

    # ============ RESPONSE TIME METRICS ============
    # Average time to respond to selections
    responded_applications = applications.filter(
        status__in=["accepted", "rejected"],
        selected_at__isnull=False,
        responded_at__isnull=False,
    )

    avg_response_time = None
    if responded_applications.exists():
        total_hours = sum(
            [
                (app.responded_at - app.selected_at).total_seconds() / 3600
                for app in responded_applications
            ]
        )
        avg_response_time = round(total_hours / responded_applications.count(), 1)

    # ============ TOP PARENTS (Most hired by) ============
    top_parents = (
        hired_gigs.filter(status__in=["completed", "active"])
        .values(
            "parent__id", "parent__email", "parent__first_name", "parent__last_name"
        )
        .annotate(gig_count=Count("id"))
        .order_by("-gig_count")[:5]
    )

    top_parents_data = [
        {
            "parent_id": item["parent__id"],
            "email": item["parent__email"],
            "name": f"{item['parent__first_name']} {item['parent__last_name']}".strip(),
            "gig_count": item["gig_count"],
        }
        for item in top_parents
    ]

    # ============ PROPOSED RATE ANALYSIS ============
    # Average proposed rate
    avg_proposed_rate = applications.aggregate(avg=Avg("proposed_rate"))["avg"] or 0

    # Proposed rate vs actual earnings comparison
    rate_comparison_data = []
    for app in applications.filter(status="accepted", gig__payment__status="completed"):
        payment = GigPayment.objects.filter(gig=app.gig, teacher=request.user).first()
        if payment:
            rate_comparison_data.append(
                {
                    "gig_title": app.gig.title,
                    "proposed_rate": float(app.proposed_rate),
                    "actual_earnings": float(payment.amount - payment.platform_fee),
                }
            )

    return Response(
        {
            # Filter metadata
            "filters": {
                "date_from": start_date.isoformat(),
                "date_to": end_date.isoformat(),
            },
            # Summary metrics
            "summary": {
                "total_applications": total_applications,
                "pending_applications": pending_applications,
                "selected_applications": selected_applications,
                "accepted_applications": accepted_applications,
                "rejected_applications": rejected_applications,
                "recent_applications": recent_applications,
                "acceptance_rate": acceptance_rate,
                "active_gigs": active_gigs,
                "completed_gigs": completed_gigs,
                "total_hired_gigs": total_hired_gigs,
                "average_rating": round(average_rating, 2),
                "total_reviews": total_reviews,
                "recent_ratings": recent_ratings,
                "total_earned": round(total_earned, 2),
                "recent_earnings": round(recent_earnings, 2),
                "avg_earnings_per_gig": round(avg_earnings_per_gig, 2),
                "avg_proposed_rate": round(avg_proposed_rate, 2),
                "avg_gig_duration_weeks": round(avg_gig_duration, 1),
                "avg_response_time_hours": avg_response_time,
                "is_premium": is_premium,
                "premium_expires_at": (
                    premium_expires_at.isoformat() if premium_expires_at else None
                ),
            },
            # Chart data
            "charts": {
                "application_trends": application_trends_data,
                "success_rate": success_rate_data,
                "gig_completion": gig_completion_data,
                "earnings_trends": earnings_trends_data,
                "rating_trends": rating_trends_data,
            },
            # Distribution data
            "distributions": {
                "applications_by_status": applications_by_status_data,
                "applications_by_subject": applications_by_subject_data,
                "applications_by_grade": applications_by_grade_data,
                "gigs_by_status": gigs_by_status_data,
                "gigs_by_subject": gigs_by_subject_data,
                "gigs_by_grade": gigs_by_grade_data,
                "earnings_by_subject": earnings_by_subject_data,
                "rating_distribution": rating_distribution_data,
            },
            # Top performers
            "top_performers": {
                "top_parents": top_parents_data,
            },
            # Additional insights
            "insights": {
                "rate_comparison": rate_comparison_data[:10],  # Limit to 10 most recent
            },
            # Premium info
            "premium": {
                "is_active": is_premium,
                "expires_at": (
                    premium_expires_at.isoformat() if premium_expires_at else None
                ),
                "current_subscription": (
                    PremiumSubscriptionSerializer(active_subscription).data
                    if active_subscription
                    else None
                ),
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def parent_stats(request):
    """Get statistics for parent dashboard with chart data"""
    if request.user.role != "parent":
        return Response({"error": "Not authorized"}, status=403)

    # ============ PARSE FILTER PARAMETERS ============
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    now = timezone.now()

    if date_from and date_to:
        try:
            start_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
        except (ValueError, AttributeError):
            start_date = now - timedelta(days=180)
            end_date = now
    else:
        start_date = now - timedelta(days=180)
        end_date = now

    thirty_days_ago = now - timedelta(days=30)

    gigs = Gig.objects.filter(parent=request.user)

    total_gigs = gigs.count()
    open_gigs = gigs.filter(status="open").count()
    active_gigs = gigs.filter(status="active").count()
    completed_gigs = gigs.filter(status="completed").count()

    # Total applications across all gigs
    total_applications = Application.objects.filter(gig__parent=request.user).count()

    # Rating statistics
    ratings = Rating.objects.filter(ratee=request.user, rater_type="teacher")
    average_rating = ratings.aggregate(avg=Avg("score"))["avg"] or 0
    total_reviews = ratings.count()

    # ============ SPENDING METRICS ============

    # Total spent (completed payments)
    total_spent = (
        GigPayment.objects.filter(parent=request.user, status="completed").aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    # Average gig budget
    avg_gig_budget = gigs.aggregate(avg=Avg("budget_min"))["avg"] or 0

    # Spending over time (last 6 months)
    spending_trends = (
        GigPayment.objects.filter(
            parent=request.user,
            status="completed",
            paid_at__gte=start_date,
            paid_at__lte=end_date,
        )
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(amount=Sum("amount"), count=Count("id"))
        .order_by("month")
    )

    spending_trends_data = [
        {
            "month": item["month"].strftime("%Y-%m"),
            "amount": float(item["amount"] or 0),
            "gig_count": item["count"],
        }
        for item in spending_trends
    ]

    # ============ GIG METRICS ============

    # Gig status distribution
    gigs_by_status = gigs.values("status").annotate(count=Count("id"))
    gigs_by_status_data = {item["status"]: item["count"] for item in gigs_by_status}

    # Gig creation over time
    gig_creation_trends = (
        gigs.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    gig_creation_data = [
        {"month": item["month"].strftime("%Y-%m"), "count": item["count"]}
        for item in gig_creation_trends
    ]

    # Gigs by subject
    gigs_by_subject = (
        gigs.values("subject").annotate(count=Count("id")).order_by("-count")[:10]
    )

    gigs_by_subject_data = [
        {"subject": item["subject"], "count": item["count"]} for item in gigs_by_subject
    ]

    # Gigs by grade
    gigs_by_grade = (
        gigs.values("grade").annotate(count=Count("id")).order_by("-count")[:10]
    )

    gigs_by_grade_data = [
        {"grade": item["grade"], "count": item["count"]} for item in gigs_by_grade
    ]

    # ============ APPLICATION METRICS ============

    # Applications over time
    application_trends = (
        Application.objects.filter(
            gig__parent=request.user,
            created_at__gte=start_date,
            created_at__lte=end_date,
        )
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    application_trends_data = [
        {"month": item["month"].strftime("%Y-%m"), "count": item["count"]}
        for item in application_trends
    ]

    # Applications by status
    applications_by_status = (
        Application.objects.filter(gig__parent=request.user)
        .values("status")
        .annotate(count=Count("id"))
    )
    applications_by_status_data = {
        item["status"]: item["count"] for item in applications_by_status
    }

    # Applications per gig (average)
    avg_applications_per_gig = total_applications / total_gigs if total_gigs > 0 else 0

    # Recent application activity (last 30 days)
    recent_applications = Application.objects.filter(
        gig__parent=request.user, created_at__gte=thirty_days_ago
    ).count()

    # ============ TEACHER SELECTION METRICS ============

    # Average time to select teacher
    gigs_with_selection = gigs.filter(
        selected_teacher__isnull=False, published_at__isnull=False
    ).annotate(selection_time=F("applications__selected_at") - F("published_at"))

    avg_selection_time = None
    if gigs_with_selection.exists():
        total_days = sum(
            [
                (app.selected_at - gig.published_at).days
                for gig in gigs.filter(
                    selected_teacher__isnull=False, published_at__isnull=False
                )
                for app in gig.applications.filter(status="selected")
                if app.selected_at and gig.published_at
            ]
        )
        count = Application.objects.filter(
            gig__parent=request.user, status="selected"
        ).count()
        if count > 0:
            avg_selection_time = round(total_days / count, 1)

    # ============ RATING METRICS ============

    # Rating distribution
    rating_distribution = (
        ratings.values("score").annotate(count=Count("id")).order_by("score")
    )

    rating_distribution_data = {str(i): 0 for i in range(1, 6)}
    for item in rating_distribution:
        rating_distribution_data[str(item["score"])] = item["count"]

    # Ratings over time
    rating_trends = (
        ratings.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"), avg_score=Avg("score"))
        .order_by("month")
    )

    rating_trends_data = [
        {
            "month": item["month"].strftime("%Y-%m"),
            "total_ratings": item["count"],
            "average_rating": round(item["avg_score"], 2),
        }
        for item in rating_trends
    ]

    # ============ TOP TEACHERS ============

    # Most hired teachers
    hired_teachers = (
        Gig.objects.filter(parent=request.user, hired_teacher__isnull=False)
        .values(
            "hired_teacher__id",
            "hired_teacher__email",
            "hired_teacher__first_name",
            "hired_teacher__last_name",
        )
        .annotate(gig_count=Count("id"))
        .order_by("-gig_count")[:5]
    )

    hired_teachers_data = [
        {
            "teacher_id": item["hired_teacher__id"],
            "email": item["hired_teacher__email"],
            "name": f"{item['hired_teacher__first_name']} {item['hired_teacher__last_name']}".strip(),
            "gig_count": item["gig_count"],
        }
        for item in hired_teachers
    ]

    # ============ BUDGET ANALYSIS ============

    # Budget ranges
    budget_ranges = [
        {"label": "0-5000", "min": 0, "max": 5000},
        {"label": "5000-10000", "min": 5000, "max": 10000},
        {"label": "10000-20000", "min": 10000, "max": 20000},
        {"label": "20000-50000", "min": 20000, "max": 50000},
        {"label": "50000+", "min": 50000, "max": 999999999},
    ]

    budget_distribution = []
    for range_item in budget_ranges:
        count = gigs.filter(
            budget_min__gte=range_item["min"], budget_min__lt=range_item["max"]
        ).count()
        budget_distribution.append({"range": range_item["label"], "count": count})

    return Response(
        {
            # Filter metadata
            "filters": {
                "date_from": start_date.isoformat(),
                "date_to": end_date.isoformat(),
            },
            # Summary metrics
            "summary": {
                "total_gigs": total_gigs,
                "open_gigs": open_gigs,
                "active_gigs": active_gigs,
                "completed_gigs": completed_gigs,
                "total_applications": total_applications,
                "recent_applications": recent_applications,
                "average_rating": round(average_rating, 2),
                "total_reviews": total_reviews,
                "total_spent": float(total_spent),
                "avg_gig_budget": round(avg_gig_budget, 2),
                "avg_applications_per_gig": round(avg_applications_per_gig, 1),
                "avg_selection_time_days": avg_selection_time,
            },
            # Chart data
            "charts": {
                "spending_trends": spending_trends_data,
                "gig_creation": gig_creation_data,
                "application_trends": application_trends_data,
                "rating_trends": rating_trends_data,
            },
            # Distribution data
            "distributions": {
                "gigs_by_status": gigs_by_status_data,
                "gigs_by_subject": gigs_by_subject_data,
                "gigs_by_grade": gigs_by_grade_data,
                "applications_by_status": applications_by_status_data,
                "rating_distribution": rating_distribution_data,
                "budget_distribution": budget_distribution,
            },
            # Top performers
            "top_performers": {
                "hired_teachers": hired_teachers_data,
            },
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    """Get comprehensive statistics for admin dashboard with chart data and filtering"""
    if request.user.role != "admin":
        return Response({"error": "Not authorized"}, status=403)

    # ============ PARSE FILTER PARAMETERS ============
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    # Calculate date range
    now = timezone.now()

    if date_from and date_to:
        # Custom date range
        try:
            start_date = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            if timezone.is_naive(start_date):
                start_date = timezone.make_aware(start_date)
            if timezone.is_naive(end_date):
                end_date = timezone.make_aware(end_date)
        except (ValueError, AttributeError):
            return Response(
                {"error": "Invalid date format. Use ISO format (YYYY-MM-DD)"},
                status=400,
            )
    else:
        # Default to last 12 months
        start_date = now - timedelta(days=365)
        end_date = now

    # Additional time periods for specific charts
    thirty_days_ago = now - timedelta(days=30)
    six_months_ago = now - timedelta(days=180)
    twelve_weeks_ago = now - timedelta(weeks=12)

    # ============ REVENUE METRICS ============

    # Total earnings breakdown (filtered by date range)
    premium_earnings = (
        PremiumSubscription.objects.filter(
            status__in=["active", "expired"],
            starts_at__gte=start_date,
            starts_at__lte=end_date,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )

    gig_earnings = (
        GigPayment.objects.filter(
            status="completed", paid_at__gte=start_date, paid_at__lte=end_date
        ).aggregate(total=Sum("platform_fee"))["total"]
        or 0
    )

    platform_earnings = premium_earnings + gig_earnings

    # Revenue over time (filtered)
    monthly_revenue = (
        GigPayment.objects.filter(
            status="completed", paid_at__gte=start_date, paid_at__lte=end_date
        )
        .annotate(month=TruncMonth("paid_at"))
        .values("month")
        .annotate(gig_revenue=Sum("platform_fee"), count=Count("id"))
        .order_by("month")
    )

    monthly_premium_revenue = (
        PremiumSubscription.objects.filter(
            status__in=["active", "expired"],
            starts_at__gte=start_date,
            starts_at__lte=end_date,
        )
        .annotate(month=TruncMonth("starts_at"))
        .values("month")
        .annotate(premium_revenue=Sum("amount"), count=Count("id"))
        .order_by("month")
    )

    # Combine monthly revenues
    revenue_by_month = {}
    for item in monthly_revenue:
        month_str = item["month"].strftime("%Y-%m")
        revenue_by_month[month_str] = {
            "month": month_str,
            "gig_revenue": float(item["gig_revenue"] or 0),
            "premium_revenue": 0,
            "total_revenue": float(item["gig_revenue"] or 0),
            "gig_count": item["count"],
            "premium_count": 0,
        }

    for item in monthly_premium_revenue:
        month_str = item["month"].strftime("%Y-%m")
        if month_str in revenue_by_month:
            revenue_by_month[month_str]["premium_revenue"] = float(
                item["premium_revenue"] or 0
            )
            revenue_by_month[month_str]["total_revenue"] += float(
                item["premium_revenue"] or 0
            )
            revenue_by_month[month_str]["premium_count"] = item["count"]
        else:
            revenue_by_month[month_str] = {
                "month": month_str,
                "gig_revenue": 0,
                "premium_revenue": float(item["premium_revenue"] or 0),
                "total_revenue": float(item["premium_revenue"] or 0),
                "gig_count": 0,
                "premium_count": item["count"],
            }

    revenue_chart_data = sorted(revenue_by_month.values(), key=lambda x: x["month"])

    # Weekly revenue (last 12 weeks or filtered)
    weekly_start = max(start_date, twelve_weeks_ago)
    weekly_revenue = (
        GigPayment.objects.filter(
            status="completed", paid_at__gte=weekly_start, paid_at__lte=end_date
        )
        .annotate(week=TruncWeek("paid_at"))
        .values("week")
        .annotate(revenue=Sum("platform_fee"), count=Count("id"))
        .order_by("week")
    )

    weekly_revenue_data = [
        {
            "week": item["week"].strftime("%Y-W%U"),
            "revenue": float(item["revenue"] or 0),
            "count": item["count"],
        }
        for item in weekly_revenue
    ]

    # ============ USER METRICS ============

    # Total users by role (all time, not filtered)
    users_by_role = (
        User.objects.filter(is_active=True).values("role").annotate(count=Count("id"))
    )
    users_by_role_data = {item["role"]: item["count"] for item in users_by_role}

    # User growth over time (filtered)
    user_growth = (
        User.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month", "role")
        .annotate(count=Count("id"))
        .order_by("month", "role")
    )

    user_growth_by_month = {}
    for item in user_growth:
        month_str = item["month"].strftime("%Y-%m")
        if month_str not in user_growth_by_month:
            user_growth_by_month[month_str] = {
                "month": month_str,
                "parent": 0,
                "teacher": 0,
                "admin": 0,
                "total": 0,
            }
        role = item["role"]
        user_growth_by_month[month_str][role] = item["count"]
        user_growth_by_month[month_str]["total"] += item["count"]

    user_growth_data = sorted(user_growth_by_month.values(), key=lambda x: x["month"])

    # Daily active users (last 30 days or filtered)
    daily_start = max(start_date, thirty_days_ago)
    daily_active_users = (
        User.objects.filter(last_login__gte=daily_start, last_login__lte=end_date)
        .annotate(day=TruncDay("last_login"))
        .values("day")
        .annotate(count=Count("id", distinct=True))
        .order_by("day")
    )

    daily_active_data = [
        {"date": item["day"].strftime("%Y-%m-%d"), "active_users": item["count"]}
        for item in daily_active_users
    ]

    # ============ GIG METRICS ============

    # Gigs by status (all time, not filtered)
    gigs_by_status = Gig.objects.values("status").annotate(count=Count("id"))
    gigs_by_status_data = {item["status"]: item["count"] for item in gigs_by_status}

    # Gig creation over time (filtered)
    gig_creation = (
        Gig.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    gig_creation_data = [
        {"month": item["month"].strftime("%Y-%m"), "count": item["count"]}
        for item in gig_creation
    ]

    # Gigs by subject (top 10, all time)
    gigs_by_subject = (
        Gig.objects.values("subject")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    gigs_by_subject_data = [
        {"subject": item["subject"], "count": item["count"]} for item in gigs_by_subject
    ]

    # Gigs by grade (top 10, all time)
    gigs_by_grade = (
        Gig.objects.values("grade").annotate(count=Count("id")).order_by("-count")[:10]
    )

    gigs_by_grade_data = [
        {"grade": item["grade"], "count": item["count"]} for item in gigs_by_grade
    ]

    # Average gig completion time (all time)
    completed_gigs = Gig.objects.filter(
        status="completed", published_at__isnull=False, closed_at__isnull=False
    )

    avg_completion_time = None
    if completed_gigs.exists():
        total_days = sum(
            [(gig.closed_at - gig.published_at).days for gig in completed_gigs]
        )
        avg_completion_time = round(total_days / completed_gigs.count(), 1)

    # Gig budget distribution (all time)
    budget_ranges = [
        {"label": "0-5000", "min": 0, "max": 5000},
        {"label": "5000-10000", "min": 5000, "max": 10000},
        {"label": "10000-20000", "min": 10000, "max": 20000},
        {"label": "20000-50000", "min": 20000, "max": 50000},
        {"label": "50000+", "min": 50000, "max": 999999999},
    ]

    budget_distribution = []
    for range_item in budget_ranges:
        count = Gig.objects.filter(
            budget_min__gte=range_item["min"], budget_min__lt=range_item["max"]
        ).count()
        budget_distribution.append({"range": range_item["label"], "count": count})

    # ============ APPLICATION METRICS ============

    # Applications over time (filtered)
    application_trends = (
        Application.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    application_trends_data = [
        {"month": item["month"].strftime("%Y-%m"), "count": item["count"]}
        for item in application_trends
    ]

    # Application status breakdown (all time)
    applications_by_status = Application.objects.values("status").annotate(
        count=Count("id")
    )
    applications_by_status_data = {
        item["status"]: item["count"] for item in applications_by_status
    }

    # Application acceptance rate over time (filtered)
    monthly_acceptance = (
        Application.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(
            total=Count("id"),
            accepted=Count("id", filter=Q(status="accepted")),
            rejected=Count("id", filter=Q(status="rejected")),
        )
        .order_by("month")
    )

    acceptance_rate_data = []
    for item in monthly_acceptance:
        total = item["total"]
        if total > 0:
            acceptance_rate = round((item["accepted"] / total) * 100, 1)
            rejection_rate = round((item["rejected"] / total) * 100, 1)
        else:
            acceptance_rate = 0
            rejection_rate = 0

        acceptance_rate_data.append(
            {
                "month": item["month"].strftime("%Y-%m"),
                "acceptance_rate": acceptance_rate,
                "rejection_rate": rejection_rate,
                "total_applications": total,
            }
        )

    # ============ PREMIUM SUBSCRIPTION METRICS ============

    # Active premium users with details (all time)
    active_premium_subs = PremiumSubscription.objects.filter(
        status="active"
    ).select_related("teacher")

    premium_users_list = []
    for sub in active_premium_subs:
        premium_users_list.append(
            {
                "id": sub.teacher.id,
                "email": sub.teacher.email,
                "first_name": sub.teacher.first_name,
                "last_name": sub.teacher.last_name,
                "subscription_id": sub.id,
                "starts_at": sub.starts_at,
                "expires_at": sub.expires_at,
                "duration_days": sub.duration_days,
                "amount": float(sub.amount),
            }
        )

    # Premium subscription trends (filtered)
    premium_trends = (
        PremiumSubscription.objects.filter(
            created_at__gte=start_date, created_at__lte=end_date
        )
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"), revenue=Sum("amount"))
        .order_by("month")
    )

    premium_trends_data = [
        {
            "month": item["month"].strftime("%Y-%m"),
            "subscriptions": item["count"],
            "revenue": float(item["revenue"] or 0),
        }
        for item in premium_trends
    ]

    # Premium subscription by duration (all time)
    subscriptions_by_duration = (
        PremiumSubscription.objects.values("duration_days")
        .annotate(count=Count("id"))
        .order_by("duration_days")
    )

    subscriptions_by_duration_data = [
        {"duration": f"{item['duration_days']} days", "count": item["count"]}
        for item in subscriptions_by_duration
    ]

    # ============ RATING METRICS ============

    # Rating distribution (all time)
    rating_distribution = (
        Rating.objects.values("score").annotate(count=Count("id")).order_by("score")
    )

    rating_distribution_data = {str(i): 0 for i in range(1, 6)}
    for item in rating_distribution:
        rating_distribution_data[str(item["score"])] = item["count"]

    # Average ratings by role (all time)
    avg_ratings_by_role = []
    for role in ["parent", "teacher"]:
        avg_rating = (
            Rating.objects.filter(rater_type=role).aggregate(avg=Avg("score"))["avg"]
            or 0
        )
        count = Rating.objects.filter(rater_type=role).count()

        avg_ratings_by_role.append(
            {
                "role": role,
                "average_rating": round(avg_rating, 2),
                "total_ratings": count,
            }
        )

    # Ratings over time (filtered)
    rating_trends = (
        Rating.objects.filter(created_at__gte=start_date, created_at__lte=end_date)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"), avg_score=Avg("score"))
        .order_by("month")
    )

    rating_trends_data = [
        {
            "month": item["month"].strftime("%Y-%m"),
            "total_ratings": item["count"],
            "average_rating": round(item["avg_score"], 2),
        }
        for item in rating_trends
    ]

    # ============ PAYMENT METRICS ============

    # Payment success rate (last 30 days or filtered)
    payment_start = max(start_date, thirty_days_ago)
    recent_payments = GigPayment.objects.filter(
        created_at__gte=payment_start, created_at__lte=end_date
    )
    total_payments = recent_payments.count()
    successful_payments = recent_payments.filter(status="completed").count()
    failed_payments = recent_payments.filter(status="failed").count()
    pending_payments = recent_payments.filter(status="pending").count()

    payment_success_rate = (
        round((successful_payments / total_payments) * 100, 1)
        if total_payments > 0
        else 0
    )

    # Average payment amount (all time)
    avg_payment_amount = (
        GigPayment.objects.filter(status="completed").aggregate(
            avg=Avg("platform_fee")
        )["avg"]
        or 0
    )

    # Payment method distribution (all time)
    payment_methods_data = [
        {
            "method": "Khalti",
            "count": GigPayment.objects.filter(status="completed").count(),
            "total_amount": float(gig_earnings),
        }
    ]

    # ============ TOP PERFORMERS ============

    # Top earning teachers (filtered by payment date)
    top_teachers = (
        GigPayment.objects.filter(
            status="completed", paid_at__gte=start_date, paid_at__lte=end_date
        )
        .values(
            "teacher__id", "teacher__email", "teacher__first_name", "teacher__last_name"
        )
        .annotate(
            total_earnings=Sum(F("amount") - F("platform_fee")), gig_count=Count("id")
        )
        .order_by("-total_earnings")[:10]
    )

    top_teachers_data = [
        {
            "teacher_id": item["teacher__id"],
            "email": item["teacher__email"],
            "name": f"{item['teacher__first_name']} {item['teacher__last_name']}".strip(),
            "total_earnings": float(item["total_earnings"] or 0),
            "completed_gigs": item["gig_count"],
        }
        for item in top_teachers
    ]

    # Top spending parents (filtered by payment date)
    top_parents = (
        GigPayment.objects.filter(
            status="completed", paid_at__gte=start_date, paid_at__lte=end_date
        )
        .values(
            "parent__id", "parent__email", "parent__first_name", "parent__last_name"
        )
        .annotate(total_spent=Sum("amount"), gig_count=Count("id"))
        .order_by("-total_spent")[:10]
    )

    top_parents_data = [
        {
            "parent_id": item["parent__id"],
            "email": item["parent__email"],
            "name": f"{item['parent__first_name']} {item['parent__last_name']}".strip(),
            "total_spent": float(item["total_spent"] or 0),
            "gigs_posted": item["gig_count"],
        }
        for item in top_parents
    ]

    # Most popular subjects by revenue (filtered)
    subject_revenue = (
        Gig.objects.filter(
            payment__status="completed",
            payment__paid_at__gte=start_date,
            payment__paid_at__lte=end_date,
        )
        .values("subject")
        .annotate(total_revenue=Sum("payment__platform_fee"), gig_count=Count("id"))
        .order_by("-total_revenue")[:10]
    )

    subject_revenue_data = [
        {
            "subject": item["subject"],
            "revenue": float(item["total_revenue"] or 0),
            "gig_count": item["gig_count"],
        }
        for item in subject_revenue
    ]

    # ============ AGGREGATE RESPONSE ============

    return Response(
        {
            # Filter metadata
            "filters": {
                "date_from": start_date.isoformat(),
                "date_to": end_date.isoformat(),
            },
            # Summary metrics
            "summary": {
                "platform_earnings": float(platform_earnings),
                "premium_earnings": float(premium_earnings),
                "gig_earnings": float(gig_earnings),
                "total_users": User.objects.filter(is_active=True).count(),
                "active_gigs": Gig.objects.filter(status="active").count(),
                "total_gigs": Gig.objects.count(),
                "total_applications": Application.objects.count(),
                "total_ratings": Rating.objects.count(),
                "active_premium_users": active_premium_subs.count(),
                "total_premium_subscriptions": PremiumSubscription.objects.count(),
                "avg_completion_time_days": avg_completion_time,
                "payment_success_rate": payment_success_rate,
                "avg_payment_amount": float(avg_payment_amount),
            },
            # Chart data
            "charts": {
                "revenue_by_month": revenue_chart_data,
                "weekly_revenue": weekly_revenue_data,
                "user_growth": user_growth_data,
                "daily_active_users": daily_active_data,
                "gig_creation": gig_creation_data,
                "application_trends": application_trends_data,
                "acceptance_rate": acceptance_rate_data,
                "premium_trends": premium_trends_data,
                "rating_trends": rating_trends_data,
            },
            # Distribution data
            "distributions": {
                "users_by_role": users_by_role_data,
                "gigs_by_status": gigs_by_status_data,
                "gigs_by_subject": gigs_by_subject_data,
                "gigs_by_grade": gigs_by_grade_data,
                "budget_distribution": budget_distribution,
                "applications_by_status": applications_by_status_data,
                "subscriptions_by_duration": subscriptions_by_duration_data,
                "rating_distribution": rating_distribution_data,
                "avg_ratings_by_role": avg_ratings_by_role,
                "payment_methods": payment_methods_data,
            },
            # Top performers
            "top_performers": {
                "teachers": top_teachers_data,
                "parents": top_parents_data,
                "subjects_by_revenue": subject_revenue_data,
            },
            # Detailed lists
            "details": {
                "premium_users": premium_users_list,
                "recent_payment_stats": {
                    "total": total_payments,
                    "completed": successful_payments,
                    "failed": failed_payments,
                    "pending": pending_payments,
                },
            },
        }
    )
