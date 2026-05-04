from django.core.management.base import BaseCommand
from django.utils import timezone
from payments.models import PremiumSubscription
from profiles.models import TeacherProfile


class Command(BaseCommand):
    help = "Check and update expired premium subscriptions"

    def handle(self, *args, **options):
        now = timezone.now()

        # Find expired subscriptions that are still marked as active
        expired_subscriptions = PremiumSubscription.objects.filter(
            status="active", expires_at__lt=now
        )

        count = 0
        for subscription in expired_subscriptions:
            # Update subscription status
            subscription.status = "expired"
            subscription.save()

            # Update teacher profile
            teacher_profile = TeacherProfile.objects.get(user=subscription.teacher)

            # Check if there are other active subscriptions
            has_other_active = PremiumSubscription.objects.filter(
                teacher=subscription.teacher, status="active"
            ).exists()

            if not has_other_active:
                teacher_profile.is_premium = False
                teacher_profile.premium_expires_at = None
                teacher_profile.save()

            count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {count} expired subscriptions")
        )
