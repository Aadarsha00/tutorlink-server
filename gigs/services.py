from django.db.models import Case, When, IntegerField


class GigService:
    @classmethod
    def get_sorted_applications(cls, gig):
        """Sort applications with premium teachers first"""
        from applications.models import Application

        applications = (
            Application.objects.filter(gig=gig, status="pending")
            .select_related("teacher", "teacher__teacher_profile")
            .annotate(
                premium_rank=Case(
                    When(
                        teacher__teacher_profile__is_premium=True,
                        teacher__teacher_profile__verification_status="verified",
                        then=1,
                    ),
                    When(
                        teacher__teacher_profile__verification_status="verified", then=2
                    ),
                    default=3,
                    output_field=IntegerField(),
                )
            )
            .order_by("premium_rank", "-created_at")
        )

        return applications
