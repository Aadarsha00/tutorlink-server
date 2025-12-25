from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from django.db.models import Sum
from accounts.models import User
from applications.models import Application
from escrow.models import EscrowTransaction
from gigs.models import Gig


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def teacher_stats(request):
    """Get statistics for teacher dashboard"""
    if request.user.role != "teacher":
        return Response({"error": "Not authorized"}, status=403)

    # Get all applications
    applications = Application.objects.filter(teacher=request.user)

    # Count by status
    total_applications = applications.count()
    pending_applications = applications.filter(status="pending").count()

    # Active gigs (gigs where teacher is hired and status is active)
    active_gigs = Gig.objects.filter(
        hired_teacher=request.user, status="active"
    ).count()

    # Total earnings (from completed escrow transactions)
    earnings = (
        EscrowTransaction.objects.filter(
            teacher=request.user, status="released"
        ).aggregate(total=Sum("teacher_amount"))["total"]
        or 0
    )

    # Calculate acceptance rate
    accepted = applications.filter(status="accepted").count()
    selected = applications.filter(
        status__in=["selected", "accepted", "rejected"]
    ).count()
    acceptance_rate = round((accepted / selected * 100) if selected > 0 else 0, 1)

    return Response(
        {
            "total_applications": total_applications,
            "pending_applications": pending_applications,
            "active_gigs": active_gigs,
            "total_earnings": float(earnings),
            "acceptance_rate": acceptance_rate,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def parent_stats(request):
    """Get statistics for parent dashboard"""
    if request.user.role != "parent":
        return Response({"error": "Not authorized"}, status=403)

    gigs = Gig.objects.filter(parent=request.user)

    total_gigs = gigs.count()
    open_gigs = gigs.filter(status="open").count()
    active_gigs = gigs.filter(status="active").count()
    completed_gigs = gigs.filter(status="completed").count()

    # Total applications across all gigs
    total_applications = Application.objects.filter(gig__parent=request.user).count()

    return Response(
        {
            "total_gigs": total_gigs,
            "open_gigs": open_gigs,
            "active_gigs": active_gigs,
            "completed_gigs": completed_gigs,
            "total_applications": total_applications,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_stats(request):
    """Get statistics for admin dashboard"""
    if request.user.role != "admin":
        return Response({"error": "Not authorized"}, status=403)

    # Escrow statistics
    total_escrow = (
        EscrowTransaction.objects.filter(status__in=["funded", "held"]).aggregate(
            total=Sum("amount")
        )["total"]
        or 0
    )

    pending_escrow = EscrowTransaction.objects.filter(status="pending_payment").count()

    active_escrow = EscrowTransaction.objects.filter(
        status__in=["funded", "held"]
    ).count()

    completed_transactions = EscrowTransaction.objects.filter(status="released").count()

    # Platform earnings (sum of all platform fees from completed transactions)
    platform_earnings = (
        EscrowTransaction.objects.filter(status="released").aggregate(
            total=Sum("platform_fee")
        )["total"]
        or 0
    )

    # Active gigs
    active_gigs = Gig.objects.filter(status="active").count()

    # Total users
    total_users = User.objects.filter(is_active=True).count()

    # Pending disputes
    pending_disputes = EscrowTransaction.objects.filter(status="disputed").count()

    return Response(
        {
            "total_escrow_amount": float(total_escrow),
            "pending_escrow": pending_escrow,
            "active_escrow": active_escrow,
            "completed_transactions": completed_transactions,
            "platform_earnings": float(platform_earnings),
            "active_gigs": active_gigs,
            "total_users": total_users,
            "pending_disputes": pending_disputes,
        }
    )
