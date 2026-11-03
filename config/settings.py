"""Django settings for the Company X feedback system."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the server dir or the repo root if present.
if os.environ.get("RIANA_ENV_FILE"):
    load_dotenv(os.environ["RIANA_ENV_FILE"])
else:
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(BASE_DIR.parent / ".env")


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    return env(key, str(default)).lower() in {"1", "true", "yes", "on"}


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "accounts",
    "feedback",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

# --- Database ---
# Supports a single DATABASE_URL (postgres://...) or discrete POSTGRES_* vars.
# Falls back to SQLite for zero-config local/test runs.
_database_url = env("DATABASE_URL", "")


def _parse_database_url(url: str) -> dict:
    from urllib.parse import urlparse

    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


if _database_url and _database_url.startswith(("postgres://", "postgresql://")):
    DATABASES = {"default": _parse_database_url(_database_url)}
elif env("POSTGRES_DB"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", "feedback"),
            "USER": env("POSTGRES_USER", "feedback"),
            "PASSWORD": env("POSTGRES_PASSWORD", "feedback"),
            "HOST": env("POSTGRES_HOST", "db"),
            "PORT": env("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "static/"

USE_TZ = True
TIME_ZONE = "UTC"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "accounts.authentication.JWTCookieAuthentication",
    ],
    # Endpoints opt in to IsAuthenticated per-view; default stays open so the
    # public questionnaire + SMS webhook keep working.
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# --- JWT / auth cookie ---
JWT_SECRET = env("JWT_SECRET", SECRET_KEY)
JWT_ACCESS_TTL_SECONDS = int(env("JWT_ACCESS_TTL_SECONDS", str(60 * 60 * 8)))  # 8h
JWT_COOKIE_NAME = env("JWT_COOKIE_NAME", "cx_access")
JWT_COOKIE_SECURE = env_bool("JWT_COOKIE_SECURE", not DEBUG)
JWT_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE", "Lax")

# --- CORS ---
# Cookies require explicit origins + credentials (cannot use "*").
_cors_origins = [o for o in env("CORS_ORIGINS", "http://localhost:3000").split(",") if o]
CORS_ALLOWED_ORIGINS = _cors_origins
CORS_ALLOW_ALL_ORIGINS = env_bool("CORS_ALLOW_ALL", False)
CORS_ALLOW_CREDENTIALS = True

# --- Application config (care rep, email, SMS, AI) ---
CARE_REP_EMAIL = env("CARE_REP_EMAIL", "care@companyx.example")

# Notify the care rep by email on every feedback (not just detractors).
NOTIFY_CARE_ON_ALL = env_bool("NOTIFY_CARE_ON_ALL", True)
# Auto-send an AI thank-you email to satisfactory (promoter/passive) customers.
AUTO_THANKYOU_ENABLED = env_bool("AUTO_THANKYOU_ENABLED", True)

SMTP_HOST = env("SMTP_HOST", "")
SMTP_PORT = int(env("SMTP_PORT", "587"))
SMTP_USER = env("SMTP_USER", "")
SMTP_PASSWORD = env("SMTP_PASSWORD", "")
SMTP_FROM = env("SMTP_FROM", "feedback@companyx.example")

AFRICASTALKING_USERNAME = env("AFRICASTALKING_USERNAME", "sandbox")
AFRICASTALKING_API_KEY = env("AFRICASTALKING_API_KEY", "")
AFRICASTALKING_SENDER_ID = env("AFRICASTALKING_SENDER_ID", "")

SMS_PROVIDER = env("SMS_PROVIDER", "africastalking")
SMSGATE_BASE_URL = env("SMSGATE_BASE_URL", "https://api.sms-gate.app/3rdparty/v1")
SMSGATE_USERNAME = env("SMSGATE_USERNAME", "")
SMSGATE_PASSWORD = env("SMSGATE_PASSWORD", "")
SMSGATE_DEVICE_ID = env("SMSGATE_DEVICE_ID", "")
SMSGATE_WEBHOOK_SECRET = env("SMSGATE_WEBHOOK_SECRET", "")

AI_PROVIDER = env("AI_PROVIDER", "mock")
AI_MODEL = env("AI_MODEL", "llama3.1")
OLLAMA_BASE_URL = env("OLLAMA_BASE_URL", "http://localhost:11434")
OPENAI_API_KEY = env("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = env("GEMINI_API_KEY", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
