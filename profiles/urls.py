# profiles/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, stats_views, rating_views, document_views
from .admin_views import (
    AdminTeacherDocumentViewSet,
    AdminParentDocumentViewSet,
    list_profile_photos,
    verify_profile_photo,
)
from payments import premium_views

# Setup router for admin viewsets
router = DefaultRouter()
router.register(
    r"admin/teacher-documents",
    AdminTeacherDocumentViewSet,
    basename="admin-teacher-documents",
)
router.register(
    r"admin/parent-documents",
    AdminParentDocumentViewSet,
    basename="admin-parent-documents",
)

urlpatterns = [
    # Include router URLs
    path("", include(router.urls)),
    # ============================================
    # PROFILE ENDPOINTS
    # ============================================
    path("teacher/", views.TeacherProfileView.as_view(), name="teacher-profile"),
    path("parent/", views.ParentProfileView.as_view(), name="parent-profile"),
    path(
        "teacher/<int:teacher_id>/",
        views.get_teacher_profile_by_id,
        name="teacher-profile-by-id",
    ),
    path(
        "parent/<int:parent_id>/",
        views.get_parent_profile_by_id,
        name="parent-profile-by-id",
    ),
    path("teachers/", views.list_teacher_profiles, name="list-teacher-profiles"),
    path(
        "admin/profile-photos/",
        list_profile_photos,
        name="admin-profile-photos",
    ),
    path(
        "admin/profile-photos/<str:user_type>/<int:profile_id>/verify/",
        verify_profile_photo,
        name="admin-verify-profile-photo",
    ),
    # ============================================
    # PROFILE COMPLETION CHECK
    # ============================================
    path(
        "check-completion/",
        document_views.check_profile_completion,
        name="check-profile-completion",
    ),
    # ============================================
    # TEACHER DOCUMENT ENDPOINTS
    # ============================================
    path(
        "teacher/documents/upload/",
        document_views.upload_teacher_document,
        name="upload-teacher-document",
    ),
    path(
        "teacher/documents/",
        document_views.list_teacher_documents,
        name="list-teacher-documents",
    ),
    path(
        "teacher/documents/<int:document_id>/delete/",
        document_views.delete_teacher_document,
        name="delete-teacher-document",
    ),
    path(
        "teacher/documents/<int:document_id>/download/",
        document_views.download_teacher_document,
        name="download-teacher-document",
    ),
    # ============================================
    # PARENT DOCUMENT ENDPOINTS
    # ============================================
    path(
        "parent/documents/upload/",
        document_views.upload_parent_document,
        name="upload-parent-document",
    ),
    path(
        "parent/documents/",
        document_views.list_parent_documents,
        name="list-parent-documents",
    ),
    path(
        "parent/documents/<int:document_id>/delete/",
        document_views.delete_parent_document,
        name="delete-parent-document",
    ),
    path(
        "parent/documents/<int:document_id>/download/",
        document_views.download_parent_document,
        name="download-parent-document",
    ),
    # ============================================
    # SUBJECT AND GRADE ENDPOINTS
    # ============================================
    path("subjects/", views.list_subjects, name="list-subjects"),
    path("grades/", views.list_grades, name="list-grades"),
    # ============================================
    # STATS ENDPOINTS
    # ============================================
    path("teacher/stats/", stats_views.teacher_stats, name="teacher-stats"),
    path("parent/stats/", stats_views.parent_stats, name="parent-stats"),
    path("admin/stats/", stats_views.admin_stats, name="admin-stats"),
    # ============================================
    # RATING ENDPOINTS
    # ============================================
    path(
        "ratings/create/", rating_views.CreateRatingView.as_view(), name="create-rating"
    ),
    path("ratings/my/", rating_views.MyRatingsView.as_view(), name="my-ratings"),
    path(
        "ratings/user/<int:user_id>/",
        rating_views.UserRatingsView.as_view(),
        name="user-ratings",
    ),
    path("ratings/stats/", rating_views.user_rating_stats, name="my-rating-stats"),
    path(
        "ratings/stats/<int:user_id>/",
        rating_views.user_rating_stats,
        name="user-rating-stats",
    ),
    path(
        "ratings/can-rate/<int:gig_id>/", rating_views.can_rate_gig, name="can-rate-gig"
    ),
    path(
        "ratings/gig/<int:gig_id>/",
        rating_views.get_rating_for_gig,
        name="get-rating-for-gig",
    ),
    path(
        "ratings/rateable-gigs/",
        rating_views.get_rateable_gigs,
        name="get-rateable-gigs",
    ),
    path("ratings/<int:rating_id>/", rating_views.update_rating, name="update-rating"),
    path(
        "ratings/<int:rating_id>/delete/",
        rating_views.delete_rating,
        name="delete-rating",
    ),
    # ============================================
    # PREMIUM ENDPOINTS
    # ============================================
    path("premium/plans/", premium_views.premium_plans),
    path("premium/eligibility/", premium_views.check_premium_eligibility),
    path("premium/subscribe/", premium_views.CreatePremiumSubscriptionView.as_view()),
    path("premium/my-subscriptions/", premium_views.my_premium_subscriptions),
    path("premium/verify-payment/", premium_views.verify_premium_payment),
    path(
        "premium/cancel/<int:subscription_id>/",
        premium_views.cancel_premium_subscription,
    ),
    path(
        "admin/subscriptions/",
        views.admin_premium_subscriptions,
        name="admin-premium-subscriptions",
    ),
]
