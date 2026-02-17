"""Django settings for project_core (local and production)."""
import os
import dj_database_url
import dotenv
import stripe
from django.core.exceptions import ImproperlyConfigured
import sys
from pathlib import Path
from django.contrib.messages import constants as messages


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# https://stackoverflow.com/questions/15209978/where-to-store-secret-keys-django
dotenv_file = os.path.join(BASE_DIR, ".env")
if os.path.isfile(dotenv_file):
    dotenv.load_dotenv(dotenv_file)

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "change-me-in-production-please",  # Local-only fallback
)

MESSAGE_TAGS = {
    messages.ERROR: 'danger',  # Map Django levels to Bootstrap classes
    messages.DEBUG: 'secondary',
}

# SECURITY WARNING: turn off debug in production
DEBUG = os.getenv("DEBUG", "True") == "True"


def env_bool(key, default=False):
    """Parse boolean-like environment variables safely."""
    return os.getenv(key, str(default)).strip().lower() in {
        "1", "true", "yes", "on"
    }

# https://github.com/joke2k/django-environ, python-decouple


def env_list(key, default=""):
    """
    Return a list of values from a comma-separated environment variable.

    Args:
        key (str): The name of the environment variable to read.
        default (str): Optional fallback value if the variable isn't set.

    Returns:
        list: A list of strings, stripped of spaces and empty values.
    """
    return [x.strip() for x in os.getenv(key, default).split(",") if x.strip()]


ALLOWED_HOSTS = env_list("ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

if DEBUG:
    # Ensure local/dev hosts work even if env var is empty
    if not ALLOWED_HOSTS:
        ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
    else:
        for host in ["127.0.0.1", "localhost", "testserver"]:
            if host not in ALLOWED_HOSTS:
                ALLOWED_HOSTS.append(host)

# HTTPS/security hardening (production only).
# Uses env overrides so local development remains unchanged.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", True)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", True)
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", True
    )
    SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", False)
# Application definition


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'django_filters',

    'cloudinary_storage',
    'cloudinary',

    'axes',

    # Crispy forms
    'crispy_forms',
    'crispy_bootstrap5',

    # Allauth
    'allauth',
    'allauth.account',

    # Apps
    'services',
    'orders',
    'core',

]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"

CRISPY_TEMPLATE_PACK = "bootstrap5"

ACCOUNT_FORMS = {
    "login": "core.forms.CustomLoginForm",
    "signup": "core.forms.CustomSignupForm",
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'axes.middleware.AxesMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Use session-based message storage
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

ROOT_URLCONF = 'project_core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR / 'templates'),
            os.path.join(BASE_DIR / 'core', 'templates', 'allauth'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'orders.context_processors.cart_total',
            ],
        },
    },
]

WSGI_APPLICATION = 'project_core.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

if DEBUG:
    # Local development: SQLite (no SSL)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # Production: require DATABASE_URL so we don't silently fall back to SQLite
    if not os.getenv("DATABASE_URL"):
        raise ImproperlyConfigured(
            "DATABASE_URL must be set when DEBUG is False."
        )
    DATABASES = {
        'default': dj_database_url.config(
            default=os.getenv('DATABASE_URL'),
            conn_max_age=600,
            ssl_require=True,  # Enforce SSL when deployed
        )
    }
    # Keep connections alive on idle dynos
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

AUTHENTICATION_BACKENDS = [

    'axes.backends.AxesBackend',

    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',

]

SITE_ID = 1

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",  # Dev default
)

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")

DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)

ACCOUNT_LOGIN_METHODS = {'username', 'email'}
ACCOUNT_SIGNUP_FIELDS = [
    'email*',
    'email2*',
    'first_name*',
    'last_name*',
    'username*',
    'password1*',
    'password2*',
]
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_USERNAME_MIN_LENGTH = 4
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': (
            'django.contrib.auth.password_validation.'
            'UserAttributeSimilarityValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.MinimumLengthValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.CommonPasswordValidator'
        ),
    },
    {
        'NAME': (
            'django.contrib.auth.password_validation.NumericPasswordValidator'
        ),
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_RESTRICTED_KEY = os.getenv('STRIPE_API_KEY')
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK = os.getenv('STRIPE_WEBHOOK', '')

# Avoid setting a None API key; prefer restricted key when present
stripe.api_key = STRIPE_RESTRICTED_KEY or STRIPE_SECRET_KEY

CLOUDINARY_STORAGE = {
    'CLOUDINARY_CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'CLOUDINARY_API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'CLOUDINARY_API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}

# Enable Cloudinary in dev with USE_CLOUDINARY_MEDIA=True
USE_CLOUDINARY_MEDIA = os.getenv("USE_CLOUDINARY_MEDIA", "False") == "True"
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STORAGES = {
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
    "default": {
        "BACKEND": (
            "cloudinary_storage.storage.MediaCloudinaryStorage"
            if ((not DEBUG) or USE_CLOUDINARY_MEDIA)
            else "django.core.files.storage.FileSystemStorage"
        )
    },
}

# Base site URL for QR codes and absolute links
SITE_URL = os.getenv("SITE_URL", "http://localhost:8000")

# django-axes: brute-force protection
AXES_ENABLED = True
AXES_FAILURE_LIMIT = int(os.getenv("AXES_FAILURE_LIMIT", 5))
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCK_OUT_AT_FAILURE = True
AXES_LOCK_OUT_BY_USER = True
AXES_LOCK_OUT_BY_IP_ONLY = False
AXES_RESET_ON_SUCCESS = True
AXES_CACHE = "default"

if "test" in sys.argv:
    AXES_ENABLED = False  # Disable Axes during tests
    # Ensure tests do not depend on network/cloud media availability.
    USE_CLOUDINARY_MEDIA = False
    STORAGES["default"]["BACKEND"] = "django.core.files.storage.FileSystemStorage"

# Logging to stdout so production errors emit tracebacks to Heroku logs
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        # Surface request errors (e.g., 500s)
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": True,
        },
    },
}
