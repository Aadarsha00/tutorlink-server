from pathlib import Path
from datetime import timedelta
import os
import pymysql

pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "django-insecure-dev-key-change-me")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.1.71"]


# Application definition

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "djoser",
    "corsheaders",
    "channels",
    # Your apps
    "accounts.apps.AccountsConfig",
    "profiles",
    "gigs",
    "applications",
    "jobs",
    "payments",
    "notifications",
    "messaging",
    "reports.apps.ReportsConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
# https://docs.djangoproject.com/en/6.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.0/howto/static-files/

STATIC_URL = "static/"

# ============================================
# CUSTOM USER MODEL
# ============================================
AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": None,
    "AUDIENCE": None,
    "ISSUER": None,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_OBTAIN_SERIALIZER": "accounts.serializers.VerifiedTokenObtainPairSerializer",
}

# ============================================
# DJOSER CONFIGURATION
# ============================================
DJOSER = {
    "LOGIN_FIELD": "email",
    "USER_CREATE_PASSWORD_RETYPE": True,
    "USERNAME_CHANGED_EMAIL_CONFIRMATION": True,
    "PASSWORD_CHANGED_EMAIL_CONFIRMATION": True,
    "SEND_CONFIRMATION_EMAIL": True,
    "SEND_ACTIVATION_EMAIL": True,
    "SET_USERNAME_RETYPE": True,
    "SET_PASSWORD_RETYPE": True,
    "PASSWORD_RESET_CONFIRM_URL": "password/reset/confirm/{uid}/{token}",
    "USERNAME_RESET_CONFIRM_URL": "email/reset/confirm/{uid}/{token}",
    "ACTIVATION_URL": "activate/{uid}/{token}",
    "SERIALIZERS": {
        "user_create": "accounts.serializers.UserCreateSerializer",
        "user": "accounts.serializers.UserSerializer",
        "current_user": "accounts.serializers.CurrentUserSerializer",
        "user_delete": "djoser.serializers.UserDeleteSerializer",
    },
    "EMAIL": {
        "activation": "djoser.email.ActivationEmail",
        "confirmation": "djoser.email.ConfirmationEmail",
        "password_reset": "djoser.email.PasswordResetEmail",
        "password_changed_confirmation": "djoser.email.PasswordChangedConfirmationEmail",
        "username_changed_confirmation": "djoser.email.UsernameChangedConfirmationEmail",
        "username_reset": "djoser.email.UsernameResetEmail",
    },
    "PERMISSIONS": {
        "user": ["rest_framework.permissions.IsAuthenticated"],
        "user_list": ["rest_framework.permissions.IsAdminUser"],
        "user_create": ["rest_framework.permissions.AllowAny"],
        "user_delete": ["rest_framework.permissions.IsAuthenticated"],
        "token_create": ["rest_framework.permissions.AllowAny"],
        "token_destroy": ["rest_framework.permissions.IsAuthenticated"],
    },
}

# ============================================
# EMAIL CONFIGURATION
# ============================================


# For Production - SMTP Backend (uncomment and configure)
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "codebits.ctrlbits@gmail.com"
EMAIL_HOST_PASSWORD = "cnzmquyauvnxewof"
DEFAULT_FROM_EMAIL = "codebits.ctrlbits@gmail.com"


CORS_ALLOW_ALL_ORIGINS = True

# For Production - Specify allowed origins (uncomment and configure)
# CORS_ALLOWED_ORIGINS = [
#     "https://yourdomain.com",
#     "https://www.yourdomain.com",
# ]

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

# ============================================
# SECURITY HEADERS
# ============================================
# Allow same-origin framing for document previews (PDFs in iframes)
X_FRAME_OPTIONS = "SAMEORIGIN"

# ============================================
# SITE CONFIGURATION (for email links)
# ============================================
DOMAIN = "localhost:5173"  # Your frontend domain
SITE_NAME = "Seekshalaya"

FRONTEND_URL = "http://localhost:5173"


ASGI_APPLICATION = "core.asgi.application"

# Channel Layers - For Development (In-Memory)
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "notifications": {
            "handlers": ["console"],
            "level": "INFO",  # Change to DEBUG for more details
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
    },
}


# settings.py - Add these configurations

from pathlib import Path

# Media files configuration
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, "media")

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10485760  # 10MB

# Allowed file extensions for verification documents
ALLOWED_DOCUMENT_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]
MAX_DOCUMENT_SIZE = 5 * 1024 * 1024  # 5MB

# Create media directories
TEACHER_DOCUMENTS_DIR = "teacher_documents"
PARENT_DOCUMENTS_DIR = "parent_documents"

KHALTI_SECRET_KEY = os.getenv("KHALTI_SECRET_KEY", "")
KHALTI_PUBLIC_KEY = os.getenv("KHALTI_PUBLIC_KEY", "")
KHALTI_BASE_URL = os.getenv("KHALTI_BASE_URL", "https://dev.khalti.com/api/v2")
KHALTI_INITIATE_URL = os.getenv(
    "KHALTI_INITIATE_URL",
    f"{KHALTI_BASE_URL.rstrip('/')}/epayment/initiate/",
)
KHALTI_LOOKUP_URL = os.getenv(
    "KHALTI_LOOKUP_URL",
    f"{KHALTI_BASE_URL.rstrip('/')}/epayment/lookup/",
)
