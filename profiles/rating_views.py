# profiles/rating_views.py
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404

from profiles.models import Rating
from profiles.serializers import RatingSerializer
from accounts.models import User


class CreateRatingView(generics.CreateAPIView):
    """Create a new rating for an active or completed gig"""

    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]


class MyRatingsView(generics.ListAPIView):
    """List all ratings given and received by current user"""

    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        filter_type = self.request.query_params.get("type", "all")

        if filter_type == "given":
            return (
                Rating.objects.filter(rater=user)
                .select_related("rater", "ratee", "gig")
                .order_by("-created_at")
            )
        elif filter_type == "received":
            return (
                Rating.objects.filter(ratee=user)
                .select_related("rater", "ratee", "gig")
                .order_by("-created_at")
            )
        else:
            return (
                Rating.objects.filter(Q(rater=user) | Q(ratee=user))
                .select_related("rater", "ratee", "gig")
                .order_by("-created_at")
            )


class UserRatingsView(generics.ListAPIView):
    """List all ratings for a specific user (public)"""

    serializer_class = RatingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        user = get_object_or_404(User, id=user_id)

        # Only show ratings received (not given)
        return (
            Rating.objects.filter(ratee=user)
            .select_related("rater", "ratee", "gig")
            .order_by("-created_at")
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_rating_stats(request, user_id=None):
    """Get rating statistics for a user"""
    if user_id:
        user = get_object_or_404(User, id=user_id)
    else:
        user = request.user

    # Determine which type of ratings to show
    if user.role == "teacher":
        # Teachers get rated by parents
        ratings = Rating.objects.filter(ratee=user, rater_type="parent")
    elif user.role == "parent":
        # Parents get rated by teachers
        ratings = Rating.objects.filter(ratee=user, rater_type="teacher")
    else:
        # Admin or others - show all ratings received
        ratings = Rating.objects.filter(ratee=user)

    # Calculate statistics
    average_rating = ratings.aggregate(avg=Avg("score"))["avg"] or 0
    total_ratings = ratings.count()

    # Rating distribution (count of each score)
    distribution = (
        ratings.values("score").annotate(count=Count("score")).order_by("score")
    )
    rating_distribution = {str(item["score"]): item["count"] for item in distribution}

    # Ensure all scores 1-5 are in distribution
    for i in range(1, 6):
        if str(i) not in rating_distribution:
            rating_distribution[str(i)] = 0

    # Recent ratings (last 5)
    recent_ratings = ratings.select_related("rater", "ratee", "gig").order_by(
        "-created_at"
    )[:5]

    data = {
        "user_id": user.id,
        "average_rating": round(average_rating, 2),
        "total_ratings": total_ratings,
        "rating_distribution": rating_distribution,
        "recent_ratings": RatingSerializer(recent_ratings, many=True).data,
    }

    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def can_rate_gig(request, gig_id):
    """Check if current user can rate a specific gig"""
    from gigs.models import Gig

    user = request.user
    gig = get_object_or_404(Gig, id=gig_id)

    # Define rateable statuses - active and all stages after
    RATEABLE_STATUSES = ["active", "completed", "disputed"]

    # Check if gig is in a rateable status
    if gig.status not in RATEABLE_STATUSES:
        return Response(
            {
                "can_rate": False,
                "reason": f"Gig must be active or completed to rate. Current status: {gig.status}",
            }
        )

    # Check if user is involved in the gig
    if user.role == "parent":
        if gig.parent != user:
            return Response(
                {"can_rate": False, "reason": "You are not the parent of this gig"}
            )
        if not gig.hired_teacher:
            return Response(
                {"can_rate": False, "reason": "No teacher was hired for this gig"}
            )
    elif user.role == "teacher":
        if gig.hired_teacher != user:
            return Response(
                {"can_rate": False, "reason": "You were not hired for this gig"}
            )
    else:
        return Response(
            {"can_rate": False, "reason": "Only parents and teachers can rate"}
        )

    # Check if already rated
    if Rating.objects.filter(rater=user, gig=gig).exists():
        return Response(
            {"can_rate": False, "reason": "You have already rated this gig"}
        )

    return Response({"can_rate": True, "reason": None})


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_rating(request, rating_id):
    """Delete a rating (only by the rater)"""
    rating = get_object_or_404(Rating, id=rating_id)

    # Only the rater can delete their rating
    if rating.rater != request.user:
        return Response(
            {"error": "You can only delete your own ratings"},
            status=status.HTTP_403_FORBIDDEN,
        )

    rating.delete()
    return Response(
        {"message": "Rating deleted successfully"}, status=status.HTTP_204_NO_CONTENT
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_rating(request, rating_id):
    """Update a rating (only by the rater)"""
    rating = get_object_or_404(Rating, id=rating_id)

    # Only the rater can update their rating
    if rating.rater != request.user:
        return Response(
            {"error": "You can only update your own ratings"},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = RatingSerializer(
        rating, data=request.data, partial=True, context={"request": request}
    )

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_rating_for_gig(request, gig_id):
    """Get the current user's rating for a specific gig (if exists)"""
    from gigs.models import Gig

    user = request.user
    gig = get_object_or_404(Gig, id=gig_id)

    try:
        rating = Rating.objects.get(rater=user, gig=gig)
        serializer = RatingSerializer(rating, context={"request": request})
        return Response(
            {"exists": True, "rating": serializer.data}, status=status.HTTP_200_OK
        )
    except Rating.DoesNotExist:
        return Response({"exists": False, "rating": None}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_rateable_gigs(request):
    """Get all gigs that the current user can rate"""
    from gigs.models import Gig

    user = request.user

    # Define rateable statuses
    RATEABLE_STATUSES = ["active", "completed", "disputed"]

    if user.role == "parent":
        # Get gigs where user is parent, teacher is hired, and status is rateable
        gigs = Gig.objects.filter(
            parent=user, hired_teacher__isnull=False, status__in=RATEABLE_STATUSES
        ).select_related("hired_teacher", "parent")

        result = []
        for gig in gigs:
            # Check if already rated
            already_rated = Rating.objects.filter(rater=user, gig=gig).exists()

            result.append(
                {
                    "gig_id": gig.id,
                    "gig_title": gig.title,
                    "gig_status": gig.status,
                    "teacher_id": gig.hired_teacher.id,
                    "teacher_name": gig.hired_teacher.get_full_name(),
                    "already_rated": already_rated,
                    "can_rate": not already_rated,
                }
            )

    elif user.role == "teacher":
        # Get gigs where user is hired teacher and status is rateable
        gigs = Gig.objects.filter(
            hired_teacher=user, status__in=RATEABLE_STATUSES
        ).select_related("hired_teacher", "parent")

        result = []
        for gig in gigs:
            # Check if already rated
            already_rated = Rating.objects.filter(rater=user, gig=gig).exists()

            result.append(
                {
                    "gig_id": gig.id,
                    "gig_title": gig.title,
                    "gig_status": gig.status,
                    "parent_id": gig.parent.id,
                    "parent_name": gig.parent.get_full_name(),
                    "already_rated": already_rated,
                    "can_rate": not already_rated,
                }
            )

    else:
        return Response(
            {"error": "Only parents and teachers can rate"},
            status=status.HTTP_403_FORBIDDEN,
        )

    return Response({"rateable_gigs": result, "count": len(result)})
