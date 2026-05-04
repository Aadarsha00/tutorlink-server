from django.urls import path
from .views import ApplicationViewSet

urlpatterns = [
    # List & Create
    path(
        "applications/",
        ApplicationViewSet.as_view({"get": "list", "post": "create"}),
        name="application-list",
    ),
    # Detail operations
    path(
        "applications/<int:pk>/",
        ApplicationViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="application-detail",
    ),
    # Custom actions
    path(
        "applications/<int:pk>/withdraw/",
        ApplicationViewSet.as_view({"post": "withdraw"}),
        name="application-withdraw",
    ),
    path(
        "applications/<int:pk>/select/",
        ApplicationViewSet.as_view({"post": "select"}),
        name="application-select",
    ),
    path(
        "applications/<int:pk>/accept/",
        ApplicationViewSet.as_view({"post": "accept"}),
        name="application-accept",
    ),
    path(
        "applications/<int:pk>/reject/",
        ApplicationViewSet.as_view({"post": "reject"}),
        name="application-reject",
    ),
]
