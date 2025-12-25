# gigs/state_machine.py
from enum import Enum
from typing import Dict, List


class GigStatus(Enum):
    DRAFT = "draft"
    OPEN = "open"
    SELECTION_PENDING = "selection_pending"
    CONFIRMATION_PENDING = "confirmation_pending"
    PAYMENT_PENDING = "payment_pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


class GigStateMachine:
    TRANSITIONS: Dict[GigStatus, List[GigStatus]] = {
        GigStatus.DRAFT: [GigStatus.OPEN, GigStatus.CANCELLED],
        GigStatus.OPEN: [GigStatus.SELECTION_PENDING, GigStatus.CANCELLED],
        GigStatus.SELECTION_PENDING: [
            GigStatus.CONFIRMATION_PENDING,
            GigStatus.OPEN,
            GigStatus.CANCELLED,
        ],
        GigStatus.CONFIRMATION_PENDING: [
            GigStatus.PAYMENT_PENDING,
            GigStatus.OPEN,
            GigStatus.CANCELLED,
        ],
        GigStatus.PAYMENT_PENDING: [GigStatus.ACTIVE, GigStatus.CANCELLED],
        GigStatus.ACTIVE: [
            GigStatus.COMPLETED,
            GigStatus.DISPUTED,
            GigStatus.CANCELLED,
        ],
        GigStatus.DISPUTED: [GigStatus.COMPLETED, GigStatus.CANCELLED],
        GigStatus.COMPLETED: [],
        GigStatus.CANCELLED: [],
    }

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        try:
            from_enum = GigStatus(from_status)
            to_enum = GigStatus(to_status)
            return to_enum in cls.TRANSITIONS.get(from_enum, [])
        except ValueError:
            return False

    @classmethod
    def get_allowed_transitions(cls, current_status: str) -> List[str]:
        try:
            status_enum = GigStatus(current_status)
            return [s.value for s in cls.TRANSITIONS.get(status_enum, [])]
        except ValueError:
            return []
