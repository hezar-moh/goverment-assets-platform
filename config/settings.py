"""Django settings for the government asset management platform.

Uses django-tenants for multi-ministry schemas, Keycloak OIDC for SSO,
DRF for REST APIs, and SimpleJWT for token authentication.
"""
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
# ALLOWED_HOSTS = ['*']
# In development we allow localhost and all tenant subdomains
# In production this should be locked to specific domains only
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '.localhost',   # This covers moh.localhost, mof.localhost etc.
    '[::1]',        # IPv6 localhost
    '192.168.100.18',  # my laptop WiFi IP for mobile access
    '172.16.20.232',
    '10.187.165.150',
]

SHARED_APPS = [
    'django_tenants',
    'tenants',
    'authentication',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'mozilla_django_oidc',
    'drf_yasg',
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'organizations',
    'assets',
]

INSTALLED_APPS = list(SHARED_APPS) + [
    app for app in TENANT_APPS if app not in SHARED_APPS
]

# Tell django-tenants which models represent a Tenant and a Domain
TENANT_MODEL = "tenants.Ministry"
TENANT_DOMAIN_MODEL = "tenants.Domain"

# When no tenant domain matches the request host,
# fall back to the public schema instead of returning 404.
# This is needed for mobile API access via IP address.
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True


# TenantMainMiddleware must be first — switches to the correct tenant schema
MIDDLEWARE = [
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'authentication.middleware.SchemaMiddleware',
    'mozilla_django_oidc.middleware.SessionRefresh',
]

# Public and tenant URL configs, currently both point to the same file
ROOT_URLCONF = 'config.urls'
PUBLIC_SCHEMA_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Uses django_tenants.postgresql_backend for schema-based multi-tenancy
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT', cast=int),
    }
}
DATABASE_ROUTERS = (
    'django_tenants.routers.TenantSyncRouter',
)

# Custom User model — must be set before first migration
AUTH_USER_MODEL = 'authentication.CustomUser'

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {'user_attributes': ('username', 'email', 'first_name', 'last_name')}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8}
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Static and media files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Dar_es_Salaam'
USE_I18N = True
USE_TZ = True


# Session and auth settings
LOGIN_URL          = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# Session expires when browser closes
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Session expires after 8 hours of inactivity even if browser stays open
# 8 hours = 28800 seconds — suitable for a government work day
SESSION_COOKIE_AGE = 28800

# Prevent JavaScript from reading the session cookie
# Protects against XSS attacks stealing the session
SESSION_COOKIE_HTTPONLY = True

# Only send session cookie over HTTPS in production
# Set to False in development because we use plain HTTP
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)

# Prevent CSRF cookie from being read by JavaScript
CSRF_COOKIE_HTTPONLY = True

# Only send CSRF cookie over HTTPS in production
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)

# Clickjacking protection — prevents our pages being
# loaded inside an iframe on another website
X_FRAME_OPTIONS = 'DENY'

# Tell browsers not to guess content types
SECURE_CONTENT_TYPE_NOSNIFF = True

# Tell browsers to always use HTTPS for this domain
# Only active in production when DEBUG=False
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)

# DRF settings — JWT + Session auth, JSON responses, custom error handler
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': None,
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': (
        'authentication.api_exception_handler.custom_exception_handler'
    ),
}
# Silences rest_framework.W001 — we use manual pagination
SILENCED_SYSTEM_CHECKS = ['rest_framework.W001']

# Swagger UI uses JWT Bearer token auth
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type':        'apiKey',
            'name':        'Authorization',
            'in':          'header',
            'description': (
                'JWT Bearer token authentication. \n\n'
                'Format: **Bearer &lt;your_access_token&gt;**\n\n'
                'Example: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
            ),
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR':      True,
    'SHOW_REQUEST_HEADERS': True,
    'DEFAULT_MODEL_RENDERING': 'example',
    'DOC_EXPANSION': 'list',
    'OPERATIONS_SORTER': 'method',
    'PERSIST_AUTH': True,
}
# SimpleJWT — access 30min, refresh 1 day, HS256 signature
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME':  timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS':  True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'TOKEN_OBTAIN_SERIALIZER': (
        'authentication.api_serializers.CustomTokenObtainPairSerializer'
    ),
}
# CORS — allow all origins in dev, lock down in production
# Allowed origins for when CORS_ALLOW_ALL_ORIGINS is False
CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=True, cast=bool)

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CORS_ALLOW_CREDENTIALS = True


# Security checks
import sys

# Warn if using the default insecure secret key in production
if not DEBUG and 'django-insecure' in SECRET_KEY:
    print(
        "WARNING: You are running in production with an insecure "
        "SECRET_KEY. Generate a new one immediately.",
        file=sys.stderr
    )

# Warn if DEBUG is True when running tests
if 'test' in sys.argv and DEBUG:
    print(
        "WARNING: Running tests with DEBUG=True. "
        "Set DEBUG=False for accurate security testing.",
        file=sys.stderr
    )


# Logging — Django warnings to file, security events to separate file
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'security.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'django.security': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'authentication': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
# Keycloak / OIDC settings
KEYCLOAK_SERVER_URL   = config('KEYCLOAK_SERVER_URL', default='http://localhost:8180')
KEYCLOAK_REALM        = config('KEYCLOAK_REALM',      default='govasset')
KEYCLOAK_CLIENT_ID    = config('KEYCLOAK_CLIENT_ID',  default='govasset-django')
KEYCLOAK_CLIENT_SECRET = config('KEYCLOAK_CLIENT_SECRET', default='')

_KEYCLOAK_BASE = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect"

OIDC_OP_AUTHORIZATION_ENDPOINT = f"{_KEYCLOAK_BASE}/auth"
OIDC_OP_TOKEN_ENDPOINT = f"{_KEYCLOAK_BASE}/token"
OIDC_OP_USER_ENDPOINT = f"{_KEYCLOAK_BASE}/userinfo"
OIDC_OP_JWKS_ENDPOINT = f"{_KEYCLOAK_BASE}/certs"
OIDC_OP_LOGOUT_ENDPOINT = f"{_KEYCLOAK_BASE}/logout"

OIDC_RP_CLIENT_ID     = KEYCLOAK_CLIENT_ID
OIDC_RP_CLIENT_SECRET = KEYCLOAK_CLIENT_SECRET
OIDC_RP_SIGN_ALGO = 'RS256'

OIDC_AUTHENTICATE_CLASS = 'mozilla_django_oidc.views.OIDCAuthenticationRequestView'
OIDC_AUTHENTICATION_CALLBACK_CLASS = 'mozilla_django_oidc.views.OIDCAuthenticationCallbackView'

LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'
LOGIN_REDIRECT_URL_FAILURE = '/login/?error=auth_failed'

OIDC_USE_PKCE = True

# Force login prompt to prevent ghost session issues during development
OIDC_AUTH_REQUEST_EXTRA_PARAMS = {'prompt': 'login'}


# Authentication backends — OIDC first, fallback to ModelBackend
AUTHENTICATION_BACKENDS = [
    'authentication.oidc_backend.GovAssetOIDCBackend',
    'django.contrib.auth.backends.ModelBackend',
]
