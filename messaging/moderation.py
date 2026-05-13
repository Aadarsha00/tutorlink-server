import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ModerationResult:
    allowed: bool
    reason: str = ""
    message: str = ""


PHONE_RE = re.compile(r"(?<!\d)(?:\+?977[\s.\-]*)?(?:\d[\s.\-]*){10}(?!\d)")

EXTERNAL_CONTACT_RE = re.compile(
    r"\b("
    r"whats\s*app|whatsapp|viber|telegram|signal|messenger|facebook|fb|"
    r"instagram|insta|email|gmail|mail me|call me|text me|dm me"
    r")\b",
    re.IGNORECASE,
)

OFF_PLATFORM_PAYMENT_RE = re.compile(
    r"\b("
    r"pay directly|direct payment|outside (?:the )?(?:app|site|platform)|"
    r"cash|bank transfer|esewa|e-sewa|khalti me|fonepay|ime pay"
    r")\b",
    re.IGNORECASE,
)

LOCATION_SHARING_RE = re.compile(
    r"\b("
    r"my address|home address|exact address|come to my|meet me at|"
    r"meet outside|send location|share location"
    r")\b",
    re.IGNORECASE,
)


BLOCK_MESSAGES = {
    "phone_number": "Phone numbers are not allowed in chat. Please keep communication inside TutorSpot.",
    "external_contact": "External contact details are not allowed. Please use TutorSpot chat.",
    "off_platform_payment": "Off-platform payment or deal messages are not allowed.",
    "location_sharing": "Exact address or private meeting details are not allowed in chat.",
    "empty": "Message cannot be empty.",
    "too_long": "Message is too long.",
}


def validate_message_body(body: str) -> ModerationResult:
    text = (body or "").strip()

    if not text:
        return ModerationResult(False, "empty", BLOCK_MESSAGES["empty"])

    if len(text) > 2000:
        return ModerationResult(False, "too_long", BLOCK_MESSAGES["too_long"])

    if PHONE_RE.search(text):
        return ModerationResult(False, "phone_number", BLOCK_MESSAGES["phone_number"])

    if EXTERNAL_CONTACT_RE.search(text):
        return ModerationResult(
            False, "external_contact", BLOCK_MESSAGES["external_contact"]
        )

    if OFF_PLATFORM_PAYMENT_RE.search(text):
        return ModerationResult(
            False, "off_platform_payment", BLOCK_MESSAGES["off_platform_payment"]
        )

    if LOCATION_SHARING_RE.search(text):
        return ModerationResult(
            False, "location_sharing", BLOCK_MESSAGES["location_sharing"]
        )

    return ModerationResult(True)
