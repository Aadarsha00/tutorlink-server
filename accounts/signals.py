from django.dispatch import receiver
from djoser.signals import user_activated


@receiver(user_activated)
def mark_email_verified(sender, user, **kwargs):
    if user.is_email_verified:
        return

    user.is_email_verified = True
    user.save(update_fields=["is_email_verified", "updated_at"])
