# profiles/premium_views.py
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from datetime import timedelta
import requests
import uuid
import logging

from .models import PremiumSubscription
from .plans import find_teacher_plan, teacher_plan_options
from profiles.models import TeacherProfile
from profiles.verification import teacher_documents_verified
from .serializers import PremiumSubscriptionSerializer

logger = logging.getLogger(__name__)


def _premium_verification_error(user, teacher_profile):
    if not teacher_profile.full_name:
        return "Complete your teacher profile before subscribing to Premium."

    if teacher_profile.kyc_photo_verified is not True:
        return "Your profile KYC photo must be verified before subscribing to Premium."

    if not teacher_documents_verified(user):
        return (
            "Your citizenship front, citizenship back, academic document, and CV "
            "must be verified before subscribing to Premium."
        )

    return None


class CreatePremiumSubscriptionView(generics.CreateAPIView):
    """Initiate a premium subscription payment"""

    serializer_class = PremiumSubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if request.user.role != "teacher":
            return Response(
                {"error": "Only teachers can subscribe to premium"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Check if teacher has a profile
        try:
            teacher_profile = TeacherProfile.objects.get(user=request.user)
        except TeacherProfile.DoesNotExist:
            return Response(
                {"error": "Teacher profile not found. Please create a profile first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        verification_error = _premium_verification_error(request.user, teacher_profile)
        if verification_error:
            return Response(
                {"error": verification_error},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if there's already an active subscription
        active_subscription = PremiumSubscription.objects.filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
            teacher=request.user,
            status="active",
        ).first()

        if active_subscription:
            return Response(
                {
                    "error": "You already have an active premium subscription",
                    "subscription": PremiumSubscriptionSerializer(
                        active_subscription
                    ).data,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        plan_option_id = request.data.get("plan_option_id") or request.data.get("plan_id")
        plan = find_teacher_plan(plan_option_id)
        if not plan:
            return Response(
                {"error": "Select a valid premium plan"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(
            data={
                "amount": plan["amount"],
                "duration_days": plan["duration_days"],
            }
        )
        if serializer.is_valid():
            subscription = serializer.save(
                teacher=request.user,
                plan_id=plan["plan_id"],
                billing_cycle=plan["billing_cycle"],
            )

            # Generate unique purchase_order_id (not khalti_pidx yet)
            purchase_order_id = f"premium_{uuid.uuid4().hex[:20]}"

            # Initiate Khalti payment
            try:
                khalti_response = self._initiate_khalti_payment(
                    subscription, request.user, purchase_order_id
                )

                if khalti_response.get("success"):
                    # Save Khalti's returned pidx
                    khalti_pidx = khalti_response.get("pidx")

                    if not khalti_pidx:
                        subscription.delete()
                        return Response(
                            {"error": "Khalti did not return a pidx"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        )

                    # Update subscription with Khalti's pidx
                    subscription.khalti_pidx = khalti_pidx
                    subscription.save()

                    logger.info(
                        f"Premium subscription initiated - purchase_order_id: {purchase_order_id}, "
                        f"khalti_pidx: {khalti_pidx}"
                    )

                    return Response(
                        {
                            "subscription": PremiumSubscriptionSerializer(
                                subscription
                            ).data,
                            "message": "Subscription created. Proceed with payment.",
                            "payment_url": khalti_response.get("payment_url"),
                            "pidx": khalti_pidx,
                        },
                        status=status.HTTP_201_CREATED,
                    )
                else:
                    subscription.delete()
                    return Response(
                        {
                            "error": "Failed to initiate payment",
                            "details": khalti_response.get("error"),
                        },
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            except Exception as e:
                logger.exception(
                    f"Premium payment initiation failed for user {request.user.id}"
                )
                subscription.delete()
                return Response(
                    {"error": f"Payment initiation failed: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def _initiate_khalti_payment(self, subscription, user, purchase_order_id):
        """Helper function to initiate Khalti payment

        Args:
            subscription: PremiumSubscription instance
            user: User instance (not request object)
            purchase_order_id: Our internal order ID

        Returns:
            dict: {'success': bool, 'payment_url': str, 'pidx': str, 'error': str}
        """
        url = settings.KHALTI_INITIATE_URL

        # Get phone number safely
        phone = "9800000003"  # Default
        try:
            if hasattr(user, "teacher_profile") and user.teacher_profile:
                phone = user.teacher_profile.phone or "9800000003"
        except Exception as e:
            logger.warning(f"Could not get phone from teacher_profile: {e}")

        payload = {
            "return_url": f"{settings.FRONTEND_URL}/premium/verify",
            "website_url": settings.FRONTEND_URL,
            "amount": int(subscription.amount * 100),
            "purchase_order_id": purchase_order_id,
            "purchase_order_name": (
                f"Teacher Premium {subscription.plan_id} - "
                f"{subscription.billing_cycle or subscription.duration_days}"
            ),
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
            logger.info(
                f"Calling Khalti API with purchase_order_id: {purchase_order_id}"
            )
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            # Log the response for debugging
            logger.info(f"Khalti Response Status: {response.status_code}")
            logger.debug(f"Khalti Response Text: {response.text}")

            # Check if response is empty
            if not response.text:
                return {
                    "success": False,
                    "error": "Empty response from payment gateway",
                }

            # Try to parse JSON
            try:
                data = response.json()
            except ValueError as e:
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
                "error": data.get("error_key")
                or data.get("detail")
                or data.get("message")
                or "Unknown error from payment gateway",
            }

        except requests.Timeout:
            return {
                "success": False,
                "error": "Payment gateway timeout. Please try again.",
            }
        except requests.ConnectionError:
            return {
                "success": False,
                "error": "Cannot connect to payment gateway. Please check your internet connection.",
            }
        except requests.RequestException as e:
            return {
                "success": False,
                "error": f"Payment gateway error: {str(e)}",
            }
        except Exception as e:
            logger.exception("Khalti API call failed")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
            }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_premium_eligibility(request):
    """Check if teacher is eligible for premium subscription"""
    if request.user.role != "teacher":
        return Response(
            {"error": "Only teachers can check premium eligibility"},
            status=status.HTTP_403_FORBIDDEN,
        )

    # Check if profile exists
    try:
        teacher_profile = TeacherProfile.objects.get(user=request.user)
    except TeacherProfile.DoesNotExist:
        return Response(
            {
                "eligible": False,
                "reason": "No teacher profile found. Please create your profile first.",
            }
        )

    # Check for active subscription
    active_subscription = PremiumSubscription.objects.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()),
        teacher=request.user,
        status="active",
    ).first()

    if active_subscription:
        return Response(
            {
                "eligible": False,
                "reason": "You already have an active premium subscription",
                "current_subscription": PremiumSubscriptionSerializer(
                    active_subscription
                ).data,
            }
        )

    verification_error = _premium_verification_error(request.user, teacher_profile)
    if verification_error:
        return Response(
            {
                "eligible": False,
                "reason": verification_error,
            }
        )

    return Response(
        {
            "eligible": True,
            "reason": None,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_premium_subscriptions(request):
    """Get current user's premium subscriptions"""
    if request.user.role != "teacher":
        return Response(
            {"error": "Only teachers can access premium subscriptions"},
            status=status.HTTP_403_FORBIDDEN,
        )

    subscriptions = PremiumSubscription.objects.filter(teacher=request.user).order_by(
        "-created_at"
    )

    serializer = PremiumSubscriptionSerializer(subscriptions, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_premium_payment(request):
    """Verify premium subscription payment with Khalti"""
    if request.user.role != "teacher":
        return Response(
            {"error": "Only teachers can verify premium payments"},
            status=status.HTTP_403_FORBIDDEN,
        )

    pidx = request.data.get("pidx")
    if not pidx:
        return Response(
            {"error": "pidx is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    logger.info(f"=== PREMIUM PAYMENT VERIFICATION ===")
    logger.info(f"User: {request.user.email} (ID: {request.user.id})")
    logger.info(f"PIDX: {pidx}")

    # Get the subscription
    try:
        subscription = PremiumSubscription.objects.get(khalti_pidx=pidx)
        logger.info(
            f"Subscription found: ID={subscription.id}, Teacher={subscription.teacher.email}, Status={subscription.status}"
        )
    except PremiumSubscription.DoesNotExist:
        logger.error(f"Subscription not found for pidx: {pidx}")
        user_subscriptions = PremiumSubscription.objects.filter(
            teacher=request.user
        ).values_list("khalti_pidx", flat=True)
        logger.error(f"User's subscription pidxs: {list(user_subscriptions)}")
        return Response(
            {
                "error": "Subscription not found",
                "detail": f"No subscription record found with pidx: {pidx[:20]}...",
                "pidx": pidx,
            },
            status=status.HTTP_404_NOT_FOUND,
        )

    # Verify the subscription belongs to the current user
    if subscription.teacher != request.user:
        logger.warning(
            f"User {request.user.email} tried to verify subscription for {subscription.teacher.email}"
        )
        return Response(
            {
                "error": "Permission denied",
                "detail": "This subscription does not belong to you",
            },
            status=status.HTTP_403_FORBIDDEN,
        )

    # If already completed, return success
    if subscription.status == "active":
        logger.info(f"Subscription {pidx} already active")
        return Response(
            {
                "success": True,
                "message": "Payment already verified",
                "subscription": PremiumSubscriptionSerializer(subscription).data,
            }
        )

    # Verify payment with Khalti
    url = settings.KHALTI_LOOKUP_URL
    headers = {
        "Authorization": f"Key {settings.KHALTI_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"pidx": pidx}

    try:
        logger.info(f"Calling Khalti lookup for pidx: {pidx}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)

        # Log response for debugging
        logger.info(f"Khalti Lookup Status: {response.status_code}")
        logger.debug(f"Khalti Lookup Response: {response.text}")

        if not response.text:
            return Response(
                {"error": "Empty response from payment gateway"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            data = response.json()
        except ValueError:
            return Response(
                {
                    "error": f"Invalid response from payment gateway: {response.text[:200]}"
                },
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
                    # Payment successful
                    subscription.status = "active"
                    subscription.starts_at = timezone.now()
                    subscription.expires_at = timezone.now() + timedelta(
                        days=subscription.duration_days
                    )
                    subscription.khalti_transaction_id = data.get("transaction_id")
                    subscription.save()

                    # Update teacher profile
                    teacher_profile = TeacherProfile.objects.get(user=request.user)
                    teacher_profile.is_premium = True
                    teacher_profile.premium_expires_at = subscription.expires_at
                    teacher_profile.save()

                logger.info(f"Premium subscription {pidx} activated successfully")

                serializer = PremiumSubscriptionSerializer(subscription)
                return Response(
                    {
                        "success": True,
                        "message": "Payment verified successfully",
                        "subscription": serializer.data,
                    }
                )
            elif payment_status == "Pending":
                logger.info(f"Subscription payment {pidx} still pending")
                return Response(
                    {
                        "success": False,
                        "message": "Payment is still being processed",
                        "status": "pending",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            elif payment_status in ["Expired", "User canceled"]:
                subscription.status = "cancelled"
                subscription.save()
                logger.info(f"Subscription payment {pidx} {payment_status}")
                return Response(
                    {
                        "success": False,
                        "message": f"Payment {payment_status.lower()}",
                        "status": payment_status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            else:
                # Payment failed or expired
                subscription.status = "cancelled"
                subscription.save()
                logger.warning(
                    f"Subscription payment {pidx} failed with status: {payment_status}"
                )
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
            {"error": "Payment verification timeout. Please try again."},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except Exception as e:
        logger.exception(f"Verification exception for pidx {pidx}")
        return Response(
            {"error": f"Verification failed: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_premium_subscription(request, subscription_id):
    """Cancel a premium subscription"""
    if request.user.role != "teacher":
        return Response(
            {"error": "Only teachers can cancel premium subscriptions"},
            status=status.HTTP_403_FORBIDDEN,
        )

    subscription = get_object_or_404(
        PremiumSubscription, id=subscription_id, teacher=request.user
    )

    if subscription.status != "active":
        return Response(
            {"error": "Only active subscriptions can be cancelled"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Update subscription status
    subscription.status = "cancelled"
    subscription.save()

    # Update teacher profile
    teacher_profile = TeacherProfile.objects.get(user=request.user)

    # Check if there are other active subscriptions
    has_other_active = PremiumSubscription.objects.filter(
        teacher=request.user, status="active"
    ).exists()

    if not has_other_active:
        teacher_profile.is_premium = False
        teacher_profile.premium_expires_at = None
        teacher_profile.save()

    return Response(
        {
            "message": "Subscription cancelled successfully",
            "subscription": PremiumSubscriptionSerializer(subscription).data,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def premium_plans(request):
    """Get available premium subscription plans"""
    plans = teacher_plan_options()
    return Response({"plans": plans, "count": len(plans)})
