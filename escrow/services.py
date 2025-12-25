# escrow/services.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from .models import EscrowTransaction, EscrowAction
from gigs.models import Gig
from notifications.services import NotificationService


class EscrowService:
    PLATFORM_FEE_PERCENTAGE = Decimal("10.0")  # 10%

    @classmethod
    @transaction.atomic
    def initiate_escrow(cls, gig: Gig, amount: Decimal) -> EscrowTransaction:
        """Create escrow transaction after teacher accepts"""
        if gig.status != "payment_pending":
            raise ValueError("Gig must be in payment_pending status")

        platform_fee = (amount * cls.PLATFORM_FEE_PERCENTAGE) / Decimal("100")
        teacher_amount = amount - platform_fee

        escrow = EscrowTransaction.objects.create(
            gig=gig,
            parent=gig.parent,
            teacher=gig.hired_teacher,
            amount=amount,
            platform_fee=platform_fee,
            teacher_amount=teacher_amount,
            status="pending_payment",
        )

        EscrowAction.objects.create(
            escrow=escrow,
            action_type="created",
            actor=gig.parent,
            notes=f"Escrow initiated for gig #{gig.id}",
        )

        return escrow

    @classmethod
    @transaction.atomic
    def verify_payment(
        cls, escrow: EscrowTransaction, khalti_token: str, khalti_response: dict
    ):
        """Verify Khalti payment and fund escrow"""
        escrow.khalti_token = khalti_token
        escrow.khalti_transaction_id = khalti_response.get("idx")
        escrow.status = "funded"
        escrow.funded_at = timezone.now()
        escrow.save()
        # Update gig status

        escrow.gig.status = "active"
        escrow.gig.save()

        # Log action
        EscrowAction.objects.create(
            escrow=escrow,
            action_type="payment_verified",
            actor=escrow.parent,
            metadata=khalti_response,
        )

        # Send notifications
        NotificationService.send_notification(
            user=escrow.teacher,
            notification_type="escrow_funded",
            title="Payment Secured",
            message=f"Escrow funded for {escrow.gig.title}",
            link=f"/teacher/gigs/{escrow.gig.id}",
        )

        NotificationService.send_notification(
            user=escrow.parent,
            notification_type="gig_started",
            title="Tuition Started",
            message=f"{escrow.gig.title} is now active",
            link=f"/parent/gigs/{escrow.gig.id}",
        )


@classmethod
@transaction.atomic
def release_payment(cls, escrow: EscrowTransaction, admin_user, notes: str = ""):
    """Admin releases payment to teacher"""
    if escrow.status != "funded":
        raise ValueError("Escrow must be funded to release")

    escrow.status = "released"
    escrow.released_at = timezone.now()
    escrow.save()

    escrow.gig.status = "completed"
    escrow.gig.closed_at = timezone.now()
    escrow.gig.save()

    EscrowAction.objects.create(
        escrow=escrow, action_type="released", actor=admin_user, notes=notes
    )

    # In production, integrate with payment gateway to transfer funds
    # For now, just notify
    NotificationService.send_notification(
        user=escrow.teacher,
        notification_type="payment_released",
        title="Payment Released",
        message=f"You received Rs. {escrow.teacher_amount} for {escrow.gig.title}",
        link=f"/teacher/earnings",
    )


@classmethod
@transaction.atomic
def refund_payment(cls, escrow: EscrowTransaction, admin_user, reason: str):
    """Admin refunds payment to parent"""
    if escrow.status not in ["funded", "disputed"]:
        raise ValueError("Cannot refund escrow in current status")

    escrow.status = "refunded"
    escrow.refunded_at = timezone.now()
    escrow.save()

    escrow.gig.status = "cancelled"
    escrow.gig.closed_at = timezone.now()
    escrow.gig.save()

    EscrowAction.objects.create(
        escrow=escrow, action_type="refunded", actor=admin_user, notes=reason
    )

    NotificationService.send_notification(
        user=escrow.parent,
        notification_type="payment_released",
        title="Payment Refunded",
        message=f"Rs. {escrow.amount} refunded for {escrow.gig.title}",
        link=f"/parent/gigs/{escrow.gig.id}",
    )
