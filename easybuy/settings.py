from pathlib import Path
import os
import sys
from urllib.parse import urlsplit
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
RUNNING_TESTS = "test" in sys.argv
RUNNING_DEVELOPMENT_SERVER = "runserver" in sys.argv or os.getenv("RUN_MAIN") == "true"


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in ("true", "1", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


def _normalize_public_base_url(value, *, default_scheme):
    value = (value or "").strip().rstrip("/")
    if not value:
        return ""
    if "://" not in value:
        value = f"{default_scheme}://{value}"
    return value.rstrip("/")


def _is_local_hostname(hostname):
    hostname = (hostname or "").strip().lower()
    return hostname in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


def _guess_public_host(hosts):
    for host in hosts:
        hostname = host.split(":", 1)[0].strip().lower()
        if not hostname or hostname == "*" or _is_local_hostname(hostname):
            continue
        return host.strip()
    return ""


DEBUG = env_bool("DEBUG", RUNNING_TESTS)

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG or RUNNING_TESTS:
        SECRET_KEY = "5nL9vQ2xR7mK4pT8cH1yB6wE3zU0aJ9sD4fG7hK2qR5tY8uI1oP6xC3vN0mL7aS"
    else:
        raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is disabled.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", "")

DEFAULT_PUBLIC_SCHEME = "https" if env_bool("SECURE_SSL_REDIRECT", not DEBUG) else "http"
PUBLIC_BASE_URL = _normalize_public_base_url(
    os.getenv("APP_BASE_URL"),
    default_scheme=DEFAULT_PUBLIC_SCHEME,
)
if not PUBLIC_BASE_URL and not RUNNING_DEVELOPMENT_SERVER and not RUNNING_TESTS:
    public_host = _guess_public_host(ALLOWED_HOSTS)
    if public_host:
        PUBLIC_BASE_URL = f"{DEFAULT_PUBLIC_SCHEME}://{public_host}"

_public_url_parts = urlsplit(PUBLIC_BASE_URL) if PUBLIC_BASE_URL else None
PUBLIC_SCHEME = (_public_url_parts.scheme if _public_url_parts else "").lower()
PUBLIC_HOST = (_public_url_parts.netloc if _public_url_parts else "").strip()

if PUBLIC_BASE_URL and PUBLIC_SCHEME in {"http", "https"}:
    CSRF_TRUSTED_ORIGINS = list(dict.fromkeys([*CSRF_TRUSTED_ORIGINS, PUBLIC_BASE_URL]))

AUTH_USER_MODEL = "core.User"


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "user",
    "easybuy_admin",
    "seller",
    "chatbot",
    "django.contrib.sites",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]

MIDDLEWARE = [
    "core.middleware.PublicHostMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

PERFORMANCE_LOGGING_ENABLED = env_bool("PERFORMANCE_LOGGING_ENABLED", DEBUG)
SLOW_REQUEST_THRESHOLD_MS = int(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "500"))

if PERFORMANCE_LOGGING_ENABLED:
    common_middleware_index = MIDDLEWARE.index("django.middleware.common.CommonMiddleware")
    MIDDLEWARE.insert(common_middleware_index + 1, "core.middleware.RequestTimingMiddleware")

if not DEBUG:
    security_middleware_index = MIDDLEWARE.index(
        "django.middleware.security.SecurityMiddleware"
    )
    MIDDLEWARE.insert(security_middleware_index + 1, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "easybuy.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "user.context_processors.notifications",
            ],
        },
    },
]

WSGI_APPLICATION = "easybuy.wsgi.application"

try:
    import dj_database_url
except ModuleNotFoundError:
    dj_database_url = None

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL and dj_database_url:
    DATABASES = {
        "default": dj_database_url.config(default=DATABASE_URL, conn_max_age=60)
    }
elif DEBUG or RUNNING_TESTS:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.mysql"),
            "NAME": os.getenv("DB_NAME", "easybuy"),
            "USER": os.getenv("DB_USER", ""),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "localhost"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                "charset": "utf8mb4",
            },
            "CONN_MAX_AGE": 60,
        }
    }

SITE_ID = 1

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

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


LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Kolkata"

USE_I18N = True

USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Keep production-style static handling for deployed environments, but let the
# local development server see freshly built assets from STATICFILES_DIRS even
# when .env sets DEBUG=False.
WHITENOISE_AUTOREFRESH = RUNNING_DEVELOPMENT_SERVER
WHITENOISE_USE_FINDERS = RUNNING_DEVELOPMENT_SERVER

CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": os.getenv("REDIS_URL", "").strip(),
            "TIMEOUT": 300,
            "KEY_PREFIX": "easybuy",
        }
        if os.getenv("REDIS_URL", "").strip()
        else {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "easybuy-performance-cache",
            "TIMEOUT": 300,
        }
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"
ACCOUNT_DEFAULT_HTTP_PROTOCOL = PUBLIC_SCHEME or ("https" if not DEBUG else "http")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

SOCIALACCOUNT_QUERY_EMAIL = True


EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER or "noreply@easybuy.local"

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_ENABLED = env_bool("OPENAI_ENABLED", bool(OPENAI_API_KEY))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
OPENAI_TIMEOUT_SECONDS = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"))
CHATBOT_WIDGET_ENABLED = env_bool("CHATBOT_WIDGET_ENABLED", False)


WHATSAPP_NOTIFICATIONS_ENABLED = os.getenv(
    "WHATSAPP_NOTIFICATIONS_ENABLED", "true"
).lower() in ("true", "1", "yes")

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin-allow-popups"

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "").strip()
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "").strip()
RAZORPAY_TEST_MODE = env_bool("RAZORPAY_TEST_MODE", True)  # Default to test mode

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    print(
        "WARNING: Razorpay keys missing! Copy .env.example to .env and add your test keys."
    )
    print("Signup: https://dashboard.razorpay.com/app/keys")

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
    }
}
SOCIALACCOUNT_LOGIN_ON_GET = True

ACCOUNT_LOGIN_METHODS = {"email", "username"}

ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]

# 3. Tell allauth which field on your core.User model is the username
ACCOUNT_USER_MODEL_USERNAME_FIELD = "username"


CELERY_BROKER_URL = os.getenv("REDIS_URL", "memory://localhost/")
CELERY_RESULT_BACKEND = os.getenv("REDIS_URL", "cache+memory://")

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Kolkata"

if RUNNING_DEVELOPMENT_SERVER:
    SESSION_COOKIE_SECURE = False
    CSRF_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_PROXY_SSL_HEADER = None
    USE_X_FORWARDED_HOST = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
else:
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
    SECURE_SSL_HOST = (
        (os.getenv("SECURE_SSL_HOST") or PUBLIC_HOST).strip() or None
    )
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = env_bool("USE_X_FORWARDED_HOST", not DEBUG)
    SECURE_HSTS_SECONDS = int(
        os.getenv("SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0")
    )
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG
    )
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
