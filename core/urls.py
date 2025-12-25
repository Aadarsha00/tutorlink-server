from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # API v1 endpoints
    path("api/v1/", include("accounts.urls")),
    path("api/v1/profiles/", include("profiles.urls")),
    path("api/v1/gigs/", include("gigs.urls")),
    path("api/v1/applications/", include("applications.urls")),
    path("api/v1/escrow/", include("escrow.urls")),
    path("api/v1/payments/", include("payments.urls")),
    path("api/v1/notifications/", include("notifications.urls")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

admin.site.site_header = "TutorLink Admin"
admin.site.site_title = "TutorLink Admin Portal"
admin.site.index_title = "Welcome to TutorLink Platform Administration"
