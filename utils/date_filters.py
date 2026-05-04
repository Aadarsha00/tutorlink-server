from datetime import timedelta
from django.utils import timezone


def resolve_date_range(time_range, date_from=None, date_to=None):
    now = timezone.now()

    if time_range == "7d":
        return now - timedelta(days=7), now
    if time_range == "30d":
        return now - timedelta(days=30), now
    if time_range == "3m":
        return now - timedelta(days=90), now
    if time_range == "6m":
        return now - timedelta(days=180), now
    if time_range == "1y":
        return now - timedelta(days=365), now
    if time_range == "custom" and date_from and date_to:
        return date_from, date_to

    return None, None  # all-time
