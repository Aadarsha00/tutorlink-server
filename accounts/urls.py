# accounts/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomUserViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register("users", CustomUserViewSet, basename="user")

urlpatterns = [
    # Djoser authentication endpoints
    path("auth/", include("djoser.urls")),
    path("auth/", include("djoser.urls.jwt")),
    # Custom user endpoints
    path("", include(router.urls)),
]

"""
===========================================
AVAILABLE API ENDPOINTS
===========================================

AUTHENTICATION ENDPOINTS (Djoser):
-----------------------------------
POST   /auth/users/                      - Register new user
POST   /auth/users/activation/           - Activate account
POST   /auth/users/resend_activation/    - Resend activation email
POST   /auth/jwt/create/                 - Login (get JWT tokens)
POST   /auth/jwt/refresh/                - Refresh access token
POST   /auth/jwt/verify/                 - Verify token validity
GET    /auth/users/me/                   - Get current user info
PUT    /auth/users/me/                   - Update current user
PATCH  /auth/users/me/                   - Partial update current user
DELETE /auth/users/me/                   - Delete current user
POST   /auth/users/set_password/         - Change password
POST   /auth/users/reset_password/       - Request password reset
POST   /auth/users/reset_password_confirm/ - Confirm password reset

CUSTOM USER ENDPOINTS:
----------------------
GET    /users/                           - List all users (admin only)
GET    /users/{id}/                      - Get user details
GET    /users/teachers/                  - List all teachers
GET    /users/parents/                   - List all parents (admin only)
GET    /users/role/?role=teacher         - Filter users by role
GET    /users/stats/                     - Get user statistics (admin only)
"""
