from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
import requests
import uuid
import logging

from .models import GigPayment
from .serializers import GigPaymentSerializer
from gigs.models import Gig
from applications.models import Application

logger = logging.getLogger(__name__)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_gig_payment(request, gig_id):
    """Initiate payment for accessing teacher contact details"""

    if request.user.role != "parent":
        return Response(
            {"error": "Only parents can make gig payments"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Get the gig
    gig = get_object_or_404(Gig, id=gig_id, parent=request.user)

    # Validate gig status
    if gig.status != "payment_pending":
        return Response(
            {"error": "Payment is not required for this gig status"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if teacher is hired
    if not gig.hired_teacher:
        return Response(
            {"error": "No teacher has been hired for this gig"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Check if payment already exists
    if hasattr(gig, "payment") and gig.payment.status == "completed":
        return Response(
            {"error": "Payment has already been completed for this gig"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Get the accepted application to determine amount
    application = Application.objects.filter(
        gig=gig, teacher=gig.hired_teacher, status="accepted"
    ).first()

    if not application:
        return Response(
            {"error": "No accepted application found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    monthly_amount = application.proposed_rate
    # Calculate platform fee: 10% of monthly rate * 4 weeks * sessions per week
    platform_fee = monthly_amount * Decimal("0.10") * 4 * gig.sessions_per_week

    # Create or get payment record
    payment, created = GigPayment.objects.get_or_create(
        gig=gig,
        defaults={
            "parent": request.user,
            "teacher": gig.hired_teacher,
            "amount": platform_fee,
            "platform_fee": platform_fee,
        },
    )

    if not created and payment.status == "completed":
        return Response(
            {"error": "Payment already completed"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Generate unique purchase_order_id
    purchase_order_id = f"gig_{uuid.uuid4().hex[:20]}"

    # Initiate Khalti payment
    try:
        khalti_response = _initiate_khalti_payment(
            payment, request.user, purchase_order_id
        )

        if khalti_response.get("success"):
            # Save Khalti's returned pidx
            khalti_pidx = khalti_response.get("pidx")

            if not khalti_pidx:
                return Response(
                    {"error": "Khalti did not return a pidx"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Update payment with Khalti's pidx
            payment.khalti_pidx = khalti_pidx
            payment.save()

            logger.info(
                f"Payment initiated - purchase_order_id: {purchase_order_id}, "
                f"khalti_pidx: {khalti_pidx}"
            )

            return Response(
                {
                    "payment": GigPaymentSerializer(payment).data,
                    "message": "Payment initiated. Proceed with payment.",
                    "payment_url": khalti_response.get("payment_url"),
                    "pidx": khalti_pidx,
                },
                status=status.HTTP_201_CREATED,
            )
        else:
            return Response(
                {
                    "error": "Failed to initiate payment",
                    "details": khalti_response.get("error"),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except Exception as e:
        logger.exception(f"Payment initiation failed for gig {gig_id}")
        return Response(
            {"error": f"Payment initiation failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def _initiate_khalti_payment(payment, user, purchase_order_id):
    """Helper function to initiate Khalti payment

    Args:
        payment: GigPayment instance
        user: User instance (not request object)
        purchase_order_id: Our internal order ID
    """
    url = "https://a.khalti.com/api/v2/epayment/initiate/"

    # Get phone number safely
    phone = "9800000003"  # Default
    try:
        if hasattr(user, "parent_profile") and user.parent_profile:
            phone = user.parent_profile.phone or "9800000003"
    except Exception as e:
        logger.warning(f"Could not get phone from parent_profile: {e}")

    payload = {
        "return_url": f"{settings.FRONTEND_URL}/payment/gig/verify",
        "website_url": settings.FRONTEND_URL,
        "amount": int(payment.platform_fee * 100),
        "purchase_order_id": purchase_order_id,
        "purchase_order_name": f"Gig Payment - {payment.gig.title}",
        "customer_info": {
            "name": f"{user.first_name} {user.last_name}".strip() or user.email,
            "email": user.email,
            "phone": phone,
        },
    }

    headers = {
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        logger.info(f"Calling Khalti API with purchase_order_id: {purchase_order_id}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if not response.text:
            return {"success": False, "error": "Empty response from payment gateway"}

        try:
            data = response.json()
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid response from payment gateway: {response.text[:200]}",
            }

        if response.status_code == 200:
            khalti_pidx = data.get("pidx")
            logger.info(
                f"Khalti success - purchase_order_id: {purchase_order_id}, "
                f"khalti_pidx: {khalti_pidx}"
            )

            return {
                "success": True,
                "payment_url": data.get("payment_url"),
                "pidx": khalti_pidx,
            }

        return {
            "success": False,
            "error": data.get("error_key") or data.get("detail") or "Unknown error",
        }

    except requests.Timeout:
        return {"success": False, "error": "Payment gateway timeout"}
    except Exception as e:
        logger.exception("Khalti API call failed")
        return {"success": False, "error": f"Payment error: {str(e)}"}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_gig_payment(request):
    """Verify gig payment with Khalti"""

    if request.user.role != "parent":
        return Response(
            {"error": "Only parents can verify gig payments"},
            status=status.HTTP_403_FORBIDDEN,
        )

    pidx = request.data.get("pidx")
    if not pidx:
        return Response(
            {"error": "pidx is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    logger.info(f"=== PAYMENT VERIFICATION ===")
    logger.info(f"User: {request.user.email} (ID: {request.user.id})")
    logger.info(f"PIDX: {pidx}")

    # Get the payment
    try:
        payment = GigPayment.objects.select_related("gig").get(khalti_pidx=pidx)
        logger.info(
            f"Payment found: ID={payment.id}, Parent={payment.parent.email}, Status={payment.status}"
        )
    except GigPayment.DoesNotExist:
        logger.error(f"Payment not found for pidx: {pidx}")
        user_payments = GigPayment.objects.filter(parent=request.user).values_list(
            "khalti_pidx", flat=True
        )
        logger.error(f"User's payment pidxs: {list(user_payments)}")
        return Response(
            {
                "error": "Payment not found",
                "detail": f"No payment record found with pidx: {pidx[:20]}...",
                "pidx": pidx,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Verify the payment belongs to the current user
    if payment.parent != request.user:
        logger.warning(
            f"User {request.user.email} tried to verify payment for {payment.parent.email}"
        )
        return Response(
            {
                "error": "Permission denied",
                "detail": "This payment does not belong to you",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # If already completed, return success
    if payment.status == "completed":
        logger.info(f"Payment {pidx} already completed")
        return Response(
            {
                "success": True,
                "message": "Payment already verified",
                "payment": GigPaymentSerializer(payment).data,
                "gig_status": payment.gig.status,
            }
        )

    # Verify the gig is in payment_pending status
    if payment.gig.status != "payment_pending":
        logger.warning(
            f"Gig {payment.gig.id} not in payment_pending status: {payment.gig.status}"
        )
        return Response(
            {
                "error": f"Gig is not in payment_pending status. Current status: {payment.gig.status}"
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify with Khalti
    url = "https://a.khalti.com/api/v2/epayment/lookup/"
    headers = {
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"pidx": pidx}

    try:
        logger.info(f"Calling Khalti lookup for pidx: {pidx}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        if not response.text:
            return Response(
                {"error": "Empty response from payment gateway"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            data = response.json()
        except ValueError:
            return Response(
                {"error": f"Invalid response: {response.text[:200]}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            f"Khalti lookup response: status_code={response.status_code}, data={data}"
        )
        payment_status = data.get("status", "").strip()

        if response.status_code == 200:
            if payment_status == "Completed":
                from django.db import transaction

                with transaction.atomic():
                    payment.status = "completed"
                    payment.paid_at = timezone.now()
                    payment.khalti_transaction_id = data.get("transaction_id")
                    payment.save()

                    gig = payment.gig
                    gig.status = "active"
                    gig.save()

                logger.info(f"Payment {pidx} completed successfully")

                return Response(
                    {
                        "success": True,
                        "message": "Payment verified successfully",
                        "payment": GigPaymentSerializer(payment).data,
                        "gig_status": gig.status,
                    }
                )

            elif payment_status == "Pending":
                logger.info(f"Payment {pidx} still pending")
                return Response(
                    {
                        "success": False,
                        "message": "Payment is still being processed",
                        "status": "pending",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )

            elif payment_status in ["Expired", "User canceled"]:
                payment.status = "failed"
                payment.save()
                logger.info(f"Payment {pidx} {payment_status}")
                return Response(
                    {
                        "success": False,
                        "message": f"Payment {payment_status.lower()}",
                        "status": payment_status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            else:
                payment.status = "failed"
                payment.save()
                logger.warning(f"Payment {pidx} failed with status: {payment_status}")
                return Response(
                    {
                        "success": False,
                        "message": "Payment verification failed",
                        "status": payment_status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            error_message = (
                data.get("detail") or data.get("error_key") or "Unknown error"
            )
            logger.error(
                f"Khalti lookup failed: status={response.status_code}, error={error_message}"
            )
            return Response(
                {
                    "success": False,
                    "message": f"Payment gateway error: {error_message}",
                    "status": "error",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    except requests.Timeout:
        logger.error(f"Khalti lookup timeout for pidx {pidx}")
        return Response(
            {"error": "Payment verification timeout"},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except Exception as e:
        logger.exception(f"Verification exception for pidx {pidx}")
        return Response(
            {"error": f"Verification failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_gig_payments(request):
    """Get current user's gig payments"""

    if request.user.role == "parent":
        payments = GigPayment.objects.filter(parent=request.user).order_by(
            "-created_at"
        )
    elif request.user.role == "teacher":
        payments = GigPayment.objects.filter(teacher=request.user).order_by(
            "-created_at"
        )
    else:
        return Response(
            {"error": "Invalid user role"}, status=status.HTTP_403_FORBIDDEN
        )

    serializer = GigPaymentSerializer(payments, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def payment_status(request, gig_id):
    """Check payment status for a gig"""

    gig = get_object_or_404(Gig, id=gig_id)

    # Check permissions
    if request.user.role == "parent" and gig.parent != request.user:
        return Response(
            {"error": "You do not have permission to view this payment"},
            status=status.HTTP_403_FORBIDDEN,
        )
    elif request.user.role == "teacher" and gig.hired_teacher != request.user:
        return Response(
            {"error": "You do not have permission to view this payment"},
            status=status.HTTP_403_FORBIDDEN,
        )

    try:
        payment = GigPayment.objects.get(gig=gig)
        return Response(
            {
                "payment_required": gig.status == "payment_pending",
                "payment_completed": payment.status == "completed",
                "payment": GigPaymentSerializer(payment).data,
            }
        )
    except GigPayment.DoesNotExist:
        return Response(
            {
                "payment_required": gig.status == "payment_pending",
                "payment_completed": False,
                "payment": None,
            }
        )
