import requests
from django.conf import settings

KHALTI_INIT_URL = "https://dev.khalti.com/api/v2/epayment/initiate/"
KHALTI_LOOKUP_URL = "https://dev.khalti.com/api/v2/epayment/lookup/"

HEADERS = {
    "Authorization": f"key {settings.KHALTI_SECRET_KEY}",
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
    res = requests.post(KHALTI_INIT_URL, json=payload, headers=HEADERS)
    res.raise_for_status()
    return res.json()


def verify_payment(pidx):
    res = requests.post(
        KHALTI_LOOKUP_URL,
        json={"pidx": pidx},
        headers=HEADERS,
    )
    res.raise_for_status()
    return res.json()
