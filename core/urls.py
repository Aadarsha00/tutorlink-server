from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import public_views

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1 endpoints
    path("api/v1/public/landing/", public_views.landing_data),
    path("api/v1/public/tutors/", public_views.tutors),
    path("api/v1/public/tutors/<int:tutor_id>/", public_views.tutor_detail),
    path("api/v1/public/gigs/", public_views.gigs),
    path("api/v1/public/gigs/<int:gig_id>/", public_views.gig_detail),
    path("api/v1/public/testimonials/", public_views.testimonials),
    path("api/v1/public/contact/", public_views.contact_message),
    path("api/v1/", include("accounts.urls")),
    path("api/v1/profiles/", include("profiles.urls")),
    path("api/v1/", include("gigs.urls")),
    path("api/v1/", include("applications.urls")),
    path("api/v1/", include("jobs.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
    path("api/v1/messaging/", include("messaging.urls")),
    path("api/v1/reports/", include("reports.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "Seekshalaya Admin"
admin.site.site_title = "Seekshalaya Admin Portal"
admin.site.index_title = "Welcome to Seekshalaya Platform Administration"
