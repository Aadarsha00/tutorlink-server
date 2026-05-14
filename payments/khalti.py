import requests
from django.conf import settings


def _headers():
    return {
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }


def initiate_payment(amount, order_id, order_name, return_url):
    payload = {
        "return_url": return_url,
        "website_url": settings.FRONTEND_URL,
        "amount": int(amount * 100),
        "purchase_order_id": order_id,
        "purchase_order_name": order_name,
    }
    res = requests.post(
        settings.KHALTI_INITIATE_URL,
        json=payload,
        headers=_headers(),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()


def verify_payment(pidx):
    res = requests.post(
        settings.KHALTI_LOOKUP_URL,
        json={"pidx": pidx},
        headers=_headers(),
        timeout=30,
    )
    res.raise_for_status()
    return res.json()
