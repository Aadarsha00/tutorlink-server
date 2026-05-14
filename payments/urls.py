from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PremiumSubscriptionViewSet
from . import premium_views, gig_views

router = DefaultRouter()
router.register("subscriptions", PremiumSubscriptionViewSet, basename="subscriptions")

urlpatterns = [
    path("", include(router.urls)),
    # Premium subscription endpoints
    path(
        "premium/subscribe/",
        premium_views.CreatePremiumSubscriptionView.as_view(),
        name="create-premium-subscription",
    ),
    path(
        "premium/my-subscriptions/",
        premium_views.my_premium_subscriptions,
        name="my-premium-subscriptions",
    ),
    path(
        "premium/verify-payment/",
        premium_views.verify_premium_payment,
        name="verify-premium-payment",
    ),
    path(
        "premium/cancel/<int:subscription_id>/",
        premium_views.cancel_premium_subscription,
        name="cancel-premium-subscription",
    ),
    path(
        "gig-payments/initiate/<int:gig_id>/",
        gig_views.initiate_gig_payment,
        name="initiate-gig-payment",
    ),
    path(
        "gig-payments/verify/", gig_views.verify_gig_payment, name="verify-gig-payment"
    ),
    path(
        "gig-payments/my-payments/", gig_views.my_gig_payments, name="my-gig-payments"
    ),
    path(
        "gig-payments/status/<int:gig_id>/",
        gig_views.payment_status,
        name="payment-status",
    ),
    path("gig-boosts/plans/", gig_views.boost_plans, name="gig-boost-plans"),
    path(
        "gig-boosts/initiate/<int:gig_id>/",
        gig_views.initiate_gig_boost,
        name="initiate-gig-boost",
    ),
    path(
        "gig-boosts/verify/",
        gig_views.verify_gig_boost,
        name="verify-gig-boost",
    ),
]
