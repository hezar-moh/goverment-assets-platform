# GOVERNMENT ASSET MANAGEMENT PLATFORM

# BEGINNER COMPLETE SYSTEM GUIDE — PART 3

## Chapters 15–20: Files, Panel Questions, Beginner Confusions, Real Examples

---

> **Chapters:** [15](#ch-15) · [16](#ch-16) · [17](#ch-17) · [18](#ch-18) · [19](#ch-19) · [20](#ch-20)

---

<a name="ch-15"></a>
## CHAPTER 15: FILES — COMPLETE REFERENCE

<a name="15-1"></a>
### 15.1 How to Read This Chapter

For every important file, this chapter explains:
- **Why it exists** — What problem does it solve?
- **Who calls it** — What other code uses this file?
- **Who imports it** — What files import from here?
- **When it runs** — At startup? On every request? On specific actions?
- **Key contents** — The most important classes/functions

<a name="15-2"></a>
### 15.2 `manage.py` — The Command Centre

**Why it exists:** Django needs an entry point for all commands. This file is it.

**When it runs:** Every time you type `python manage.py <command>`. Never imported by other code.

**Key line:**
```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
```
This tells Django where to find ALL configuration.

**Commands you can run through it:**
```
python manage.py runserver          # Start the website
python manage.py makemigrations     # Prepare database changes
python manage.py migrate            # Apply database changes
python manage.py migrate_schemas    # Apply changes to all schemas
python manage.py createsuperuser    # Create admin account
python manage.py setup_demo_data    # Create demo data
python manage.py shell              # Open Python command line
python manage.py test               # Run automated tests
```

<a name="15-3"></a>
### 15.3 `config/settings.py` — The Central Brain (619 lines)

**Why it exists:** Every setting for the entire project lives here. Without it, Django wouldn't know what database to use, what apps are installed, or how to handle authentication.

**Who calls it:** `manage.py` (line: `DJANGO_SETTINGS_MODULE = 'config.settings'`). Every file that imports `from django.conf import settings`.

**Key sections:**

| Lines | What they configure | Why it matters |
|-------|-------------------|----------------|
| 28-70 | SHARED_APPS + TENANT_APPS | Which apps are shared vs per-ministry |
| 135-143 | DATABASES | PostgreSQL connection |
| 182-187 | AUTH_USER_MODEL | Uses our CustomUser, not Django's default |
| 217-235 | SIMPLE_JWT | Token lifetimes, rotation, blacklisting |
| 461-510 | LOGGING | Writes to django.log + security.log |
| 527-598 | OIDC / Keycloak | SSO configuration |

**Key settings explained simply:**

```python
SHARED_APPS = [
    'django_tenants',    # Multi-tenancy system
    'tenants',           # Ministry model
    'authentication',    # User accounts — ONE table for ALL ministries
]

TENANT_APPS = [
    'organizations',     # Org hierarchy — SEPARATE per ministry
    'assets',            # Assets — SEPARATE per ministry
]
```

```python
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        # Special! Adds SET search_path before every query
    }
}
```

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

#### 15.3.1 `config/settings.py` — Complete Setting-by-Setting Deep Dive

Every significant setting in `config/settings.py`, what it does, and why it's configured that way:

**A) Multi-Tenancy Settings (Lines 20-70)**

```python
SHARED_APPS = [
    'django_tenants',
    'tenants',
    'authentication',
    # ... Django built-ins (django.contrib.admin, etc.)
]

TENANT_APPS = [
    'organizations',
    'assets',
    # ... all per-ministry apps
]

TENANT_MODEL = "tenants.Ministry"
TENANT_DOMAIN_MODEL = "tenants.Domain"

SHOW_PUBLIC_IF_NO_TENANT_FOUND = True
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `SHARED_APPS` | Apps whose tables live in the `public` schema | Authentication, tenants, and Django admin must be shared across all ministries |
| `TENANT_APPS` | Apps whose tables are duplicated in EVERY ministry schema | Each ministry gets its own assets, organizations, audit logs |
| `TENANT_MODEL` | Which model represents a ministry/tenant | Points to `tenants.Ministry` — each row = one ministry |
| `TENANT_DOMAIN_MODEL` | Which model maps URLs to tenants | Points to `tenants.Domain` — each row = one domain name |
| `SHOW_PUBLIC_IF_NO_TENANT_FOUND` | Fallback behavior when domain is unknown | `True` in dev (allows IP-based access). `False` in production |

**B) Django Apps (Lines 73-98)**

```python
INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]
```

| Setting | What It Does | Why Important |
|---------|-------------|---------------|
| `INSTALLED_APPS` | ALL apps the project uses | Combines shared + tenant apps. django-tenants replaces the default `django.contrib.admin` with its own version |
| `django_tenants` | Multi-tenancy framework | Must be first in the list for schema routing to work |

**C) Middleware Order (Lines 100-130)**

```python
MIDDLEWARE = [
    'django_tenants.middleware.maintenance.MaintenanceModeMiddleware',
    'django_tenants.middleware.TenantMainMiddleware',
    # ... standard Django middleware
    'authentication.middleware.SchemaMiddleware',
]
```

| Middleware | Lines | What It Does | Why Order Matters |
|-----------|-------|-------------|-------------------|
| `TenantMainMiddleware` | 1st active | Sets `search_path` based on domain | MUST run before any view or auth code |
| `AuthenticationMiddleware` | Middle | Attaches `request.user` | Must run after session, before our SchemaMiddleware |
| `SchemaMiddleware` | Near end | Sets `request.schema_name` from user profile | Runs AFTER user is authenticated |

**D) Database Configuration (Lines 135-145)**

```python
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': 'gov_asset_platform',
        'USER': 'postgres',
        'PASSWORD': '...',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {
            'options': '-c search_path=public'
        }
    }
}
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `ENGINE` | Database driver | `django_tenants.postgresql_backend` — custom engine that sets `search_path` on every query |
| `NAME` | Database name | `gov_asset_platform` — the PostgreSQL database |
| `USER` | Database user | `postgres` (dev) or a restricted user (production) |
| `OPTIONS` | Extra connection parameters | Initial `search_path` set to `public` on connection |

**E) Authentication (Lines 180-187)**

```python
AUTH_USER_MODEL = 'authentication.CustomUser'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'authentication.oidc_backend.CustomOIDCBackend',
]
LOGIN_URL = 'login'
LOGOUT_REDIRECT_URL = 'login'
```

| Setting | What It Does | Why Important |
|---------|-------------|---------------|
| `AUTH_USER_MODEL` | Which model is the user | We use `CustomUser` (with role + ministry_schema) instead of Django's default |
| `AUTHENTICATION_BACKENDS` | Login methods | First: API login. Second: Keycloak SSO |
| `LOGIN_URL` | Where unauthenticated users go | Points to our custom login page |

**F) Session and CSRF (Lines 192-200)**

```python
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 28800  # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = False   # Needed for mobile web views
CSRF_COOKIE_SAMESITE = 'Lax'
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `SESSION_ENGINE` | Where sessions are stored | Database (shared public schema) — persists across restarts |
| `SESSION_COOKIE_AGE` | Session lifetime | 8 hours (long enough for a workday) |
| `SESSION_EXPIRE_AT_BROWSER_CLOSE` | Auto-logout | Yes — closes tab = logs out |
| `CSRF_COOKIE_HTTPONLY` | JS access to CSRF token | `False` — mobile web views need JS to read the token |

**G) SimpleJWT Configuration (Lines 217-235)**

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_OBTAIN_SERIALIZER': 'authentication.api_serializers.CustomTokenObtainPairSerializer',
}
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `ACCESS_TOKEN_LIFETIME` | How long a JWT works | 30 minutes — short enough to limit damage if stolen |
| `REFRESH_TOKEN_LIFETIME` | How long you can get new tokens | 1 day — user must re-login daily |
| `ROTATE_REFRESH_TOKENS` | New refresh token each time | `True` — old refresh tokens stop working |
| `BLACKLIST_AFTER_ROTATION` | Kill old refresh tokens | `True` — prevents replay of old tokens |
| `TOKEN_OBTAIN_SERIALIZER` | Custom login serializer | Our serializer adds role + ministry_schema to the token payload |

**H) Django REST Framework (Lines 240-260)**

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'user': '100/hour',
    },
}
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `DEFAULT_AUTHENTICATION_CLASSES` | How API auth works | JWT Bearer tokens (not sessions) |
| `DEFAULT_PERMISSION_CLASSES` | Default access rule | Must be authenticated (no anonymous API access) |
| `PAGE_SIZE` | API list results per page | 20 items (user can override with `?page_size=`) |
| `DEFAULT_THROTTLE_RATES` | Rate limiting | 100 requests per user per hour — prevents abuse |
| `PAGE_SIZE` | Pagination default | 20 — balances response size with usability |

**I) django-tenants Specific Settings (Lines 270-290)**

```python
TENANT_LIMIT_SET_CALLS = True
TENANT_CREATION_SCRIPT = 'tenants.utils.create_tenant'
PGEXTRA_SCHEMA = 'public'
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `TENANT_LIMIT_SET_CALLS` | Optimize search_path calls | `True` — reduces database calls on every query |
| `TENANT_CREATION_SCRIPT` | Custom tenant creation | Points to our `create_tenant()` function in `tenants/utils.py` |

**J) Swagger / OpenAPI (Lines 295-320)**

```python
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': ['get', 'post', 'put', 'delete', 'patch'],
}
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `SECURITY_DEFINITIONS` | How to authenticate in Swagger UI | Bearer token (JWT) — user pastes token in Swagger UI |
| `USE_SESSION_AUTH` | Session-based auth in Swagger | `False` — we use JWT, not sessions, for API auth |

**K) OIDC / Keycloak (Lines 527-598)**

```python
OIDC_RP_CLIENT_ID = 'govasset-platform'
OIDC_RP_CLIENT_SECRET = '...'
OIDC_OP_AUTHORIZATION_ENDPOINT = 'http://localhost:8180/realms/govasset/protocol/openid-connect/auth'
OIDC_OP_TOKEN_ENDPOINT = 'http://localhost:8180/realms/govasset/protocol/openid-connect/token'
OIDC_OP_USER_ENDPOINT = 'http://localhost:8180/realms/govasset/protocol/openid-connect/userinfo'
OIDC_OP_JWKS_ENDPOINT = 'http://localhost:8180/realms/govasset/protocol/openid-connect/certs'
OIDC_RP_SIGN_ALGO = 'RS256'
LOGIN_REDIRECT_URL = '/dashboard/'
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `OIDC_RP_CLIENT_ID` | Our app's ID in Keycloak | Must match the client created in Keycloak admin console |
| `OIDC_OP_*_ENDPOINT` | Keycloak server URLs | Points to local Keycloak (dev) or production Keycloak |
| `OIDC_RP_SIGN_ALGO` | JWT signing algorithm | `RS256` — asymmetric (public/private key), more secure than HS256 |

**L) Logging (Lines 461-510)**

```python
LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {message}', 'style': '{'},
    },
    'handlers': {
        'django_file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
        },
        'security_file': {
            'class': 'logging.FileHandler',
            'filename': 'logs/security.log',
        },
    },
    'loggers': {
        'django': {'handlers': ['django_file'], 'level': 'INFO'},
        'security': {'handlers': ['security_file'], 'level': 'INFO'},
    },
}
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `django` logger | General errors + warnings | Goes to `logs/django.log` — for debugging |
| `security` logger | Auth events (logins, lockouts) | Goes to `logs/security.log` — for security audits |

**M) Security Headers (Lines 430-460)**

```python
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_HTTPONLY = True
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `SECURE_BROWSER_XSS_FILTER` | Prevents XSS attacks | Enables browser's built-in XSS filter |
| `X_FRAME_OPTIONS` | Prevents clickjacking | `DENY` — our pages cannot be embedded in iframes |
| `SESSION_COOKIE_HTTPONLY` | Prevents JS cookie theft | `True` — JavaScript cannot read session cookie |

**N) Static and Media Files (Lines 150-165)**

```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

| Setting | What It Does | Why This Value |
|---------|-------------|----------------|
| `STATIC_URL` | URL prefix for static files | `/static/` — Nginx serves from this URL path |
| `STATIC_ROOT` | Where `collectstatic` puts files | `staticfiles/` directory — Nginx reads from here |
| `MEDIA_ROOT` | Where uploaded files are stored | `media/` directory — user-uploaded images, PDFs |

**Quick Reference — What to Change for Common Tasks:**

| Task | Setting to Change | Example |
|------|------------------|---------|
| Add a new app | `INSTALLED_APPS` | Add to SHARED_APPS or TENANT_APPS |
| Change JWT expiry | `SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']` | `timedelta(hours=1)` |
| Change rate limit | `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']` | `'user': '1000/hour'` |
| Add a middleware | `MIDDLEWARE` list | Insert at correct position |
| Change database | `DATABASES['default']` | Change ENGINE, HOST, etc. |
| Point to production Keycloak | `OIDC_OP_*` endpoints | Change URLs to production Keycloak |
| Disable IP-based access | `SHOW_PUBLIC_IF_NO_TENANT_FOUND` | Set to `False` |
| Add new role-based permission | `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES']` | Add custom permission class |

<a name="15-4"></a>
### 15.4 `config/urls.py` — The URL Directory (169 lines)

**Why it exists:** Maps every web address to the code that handles it.

**Who imports it:** Django itself reads it at startup. Other files never import it.

**Structure:**
```python
urlpatterns = [
    path('login/',   login_view,     name='login'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('assets/',  asset_list_view, name='asset_list'),
    path('api/',     include('authentication.api_urls')),
    path('api/docs/', schema_view.with_ui('swagger')),
    path('oidc/',    include('mozilla_django_oidc.urls')),
]
```

**Key insight:** A URL like `/api/auth/login/` is resolved in two steps:
1. `/api/` matches in `config/urls.py` → goes to `authentication/api_urls.py`
2. `auth/login/` matches in `api_urls.py` → calls `LoginAPIView`

<a name="15-5"></a>
### 15.5 `authentication/models.py` — User Database Design (199 lines)

**Why it exists:** Defines the database tables for user accounts, pending access, and login attempts.

**Who imports it:** `authentication/admin.py`, `authentication/api_serializers.py`, views that query users.

**Three models:**

**CustomUser (lines 5-62):**
```python
class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    ministry_schema = models.CharField(max_length=63, blank=True, null=True)
    keycloak_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
```
- `role`: 5 choices (SUPER_ADMIN through AUDITOR)
- `ministry_schema`: Which PG schema this user belongs to
- `keycloak_id`: Links Django account to Keycloak account

**PendingAccess (lines 64-136):**
```python
class PendingAccess(models.Model):
    username = models.CharField(max_length=150)
    email = models.CharField(max_length=254, blank=True)
    keycloak_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(choices=["PENDING", "APPROVED", "REJECTED"], default="PENDING")
    attempted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True)
```
Used when someone authenticates with Keycloak but has no Django profile. Admin must review.

**LoginAttempt (lines 139-199):**
```python
class LoginAttempt(models.Model):
    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
    username = models.CharField(max_length=150, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
```
Brute force protection. Tracks failures per username+IP.

<a name="15-6"></a>
### 15.6 `authentication/api_views.py` — Mobile Auth API (473 lines)

**Why it exists:** Handles login/logout/refresh for the mobile app via REST API.

**Who imports it:** `authentication/api_urls.py` mounts these views to URLs.

**Classes:**

| Class | Endpoint | Purpose |
|-------|----------|---------|
| LoginAPIView | POST /api/auth/login/ | Login with brute-force check + audit |
| RefreshTokenAPIView | POST /api/auth/refresh/ | Refresh expired access token |
| MeAPIView | GET /api/auth/me/ | Get current user's profile |
| VerifyTokenAPIView | GET /api/auth/verify-token/ | Verify token for external systems |
| LogoutAPIView | POST /api/auth/logout/ | Logout + blacklist token |

**Key logic — LoginAPIView (lines 76-172):**
1. Check brute force lockout
2. Validate credentials
3. If failed: record attempt, maybe lock account
4. If success: clear attempts, create JWT, record audit

**Key logic — VerifyTokenAPIView (lines 331-398):**
Returns user info for other government groups to validate tokens.

<a name="15-7"></a>
### 15.7 `authentication/api_permissions.py` — API Bouncers (117 lines)

**Why it exists:** Controls who can access each API endpoint.

**Who imports it:** `authentication/api_views.py`, `assets/api_views.py`, `organizations/api_views.py`.

**Permission classes:**

| Class | Allows |
|-------|--------|
| IsSuperAdmin | SUPER_ADMIN only |
| IsMinistryAdmin | SUPER_ADMIN, MINISTRY_ADMIN |
| IsAgencyManagerOrAbove | SUPER_ADMIN, MINISTRY_ADMIN, AGENCY_MANAGER |
| CanManageAssets | Everyone for read; non-auditors for write |
| CanDeleteAssets | SUPER_ADMIN, MINISTRY_ADMIN only |
| CanViewAuditLogs | SUPER_ADMIN, MINISTRY_ADMIN, AUDITOR |
| HasMinistrySchema | Anyone with ministry_schema (Super Admin exempt) |

<a name="15-8"></a>
### 15.8 `authentication/oidc_backend.py` — Keycloak Bridge (146 lines)

**Why it exists:** Connects Keycloak authentication to Django user accounts.

**Who imports it:** `config/settings.py` — it is listed in `AUTHENTICATION_BACKENDS`.

**Three methods:**
```python
def filter_users_by_claims(self, claims):
    # Find existing Django user by keycloak_id or username
    
def create_user(self, claims):
    # BLOCKED — creates PendingAccess instead
    
def update_user(self, user, claims):
    # Updates role and ministry_schema from Keycloak attributes
```

<a name="15-9"></a>
### 15.9 `authentication/middleware.py` — Schema Switcher (51 lines)

**Why it exists:** Sets the correct PostgreSQL schema for every request.

**Who imports it:** `config/settings.py` — listed in MIDDLEWARE.

```python
class SchemaMiddleware:
    def process_request(self, request):
        if request.user.is_authenticated:
            request.schema_name = request.user.ministry_schema or 'public'
        else:
            request.schema_name = 'public'
```

<a name="15-10"></a>
### 15.10 `authentication/decorators.py` — Web Page Bouncers (73 lines)

**Why it exists:** Controls who can access web pages based on role.

**Who imports it:** `authentication/views.py`, `assets/views.py`, `organizations/views.py`, `tenants/views.py`.

**Decorators:**
```python
@login_required_custom           # Must be logged in
@role_required('MINISTRY_ADMIN') # Must have specific role
@ministry_isolation_check        # Must have a ministry schema
```

<a name="15-11"></a>
### 15.11 `authentication/dashboard_views.py` — Home Page (145 lines)

**Why it exists:** Shows statistics on the dashboard.

**Who imports it:** `config/urls.py` — `/` and `/dashboard/` map here.

**Logic:**
- Super Admin: total ministries, users, assets across ALL schemas
- Ministry user: assets by status, expiry warnings (red/amber/yellow), recent audit

<a name="15-12"></a>
### 15.12 `authentication/user_views.py` — User Management

**Why it exists:** Web pages for administrators to manage users.

**Pages:**
- `/users/` — List users
- `/users/create/` — Create user (in BOTH Django AND Keycloak)
- `/users/5/edit/` — Edit user
- `/users/5/toggle-active/` — Enable/disable
- `/users/5/reset-password/` — Reset password

<a name="15-13"></a>
### 15.13 `authentication/pending_access_views.py` — Access Approvals

**Why it exists:** Lets admins review blocked login requests.

**Pages:**
- `/pending-access/` — List pending requests
- `/pending-access/5/review/` — Approve or reject
- `/pending-access/clear/` — Clear old entries

<a name="15-14"></a>
### 15.14 `authentication/keycloak_admin.py` — Keycloak API (295 lines)

**Why it exists:** Lets Django create/manage users in Keycloak automatically.

**Who imports it:** `authentication/user_views.py` — when creating users.

**Methods:**
```python
create_user(username, password, role, ministry_schema)  # Creates in Keycloak
delete_user(keycloak_id)                                # Removes from Keycloak
update_user(keycloak_id, ...)                           # Updates attributes
reset_password(keycloak_id, new_password)               # Resets password
```

<a name="15-15"></a>
### 15.15 `authentication/api_serializers.py` — Data Formatters (222 lines)

**Why it exists:** Converts database objects to JSON for API responses.

**Who imports it:** `authentication/api_views.py`.

**Serializers:**
```python
CustomTokenObtainPairSerializer  # JWT token with role, ministry_schema
UserProfileSerializer            # User info for /api/auth/me/
AssetCategorySerializer          # Category for dropdowns
AssetSerializer                  # Full asset data for mobile
OrgUnitSerializer                # Org hierarchy
AuditLogSerializer               # Audit entries
```

<a name="15-16"></a>
### 15.16 `authentication/pagination.py` — Page Splitter (36 lines)

**Why it exists:** Splits long lists into pages (20 items per page).

**Who imports it:** Views that list items.

```python
def paginate_queryset(queryset, request, per_page=20):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get('page', 1)
    page = paginator.page(page_number)
    return page, paginator
```

<a name="15-17"></a>
### 15.17 `authentication/api_urls.py` — API Directory (89 lines)

**Why it exists:** Maps API URLs to view classes.

**Who imports it:** `config/urls.py` (`path('api/', include(...))`).

**Endpoints:**
```
auth/login/           → LoginAPIView
auth/refresh/         → RefreshTokenAPIView
auth/me/              → MeAPIView
auth/verify-token/    → VerifyTokenAPIView
auth/logout/          → LogoutAPIView
assets/               → AssetListCreateAPIView
assets/<int:asset_id>/ → AssetDetailAPIView
assets/categories/    → AssetCategoryListAPIView
org-units/            → OrgUnitListAPIView
audit-logs/           → AuditLogListAPIView
dashboard/stats/      → DashboardStatsAPIView
```

<a name="15-18"></a>
### 15.18 `assets/models.py` — Asset Database Design (245 lines)

**Why it exists:** Defines Asset and AssetCategory database tables.

**Who imports it:** `assets/views.py`, `assets/api_views.py`, `assets/admin.py`.

**AssetCategory:**
```python
class AssetCategory(models.Model):
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    is_active = models.BooleanField(default=True)
```

**Asset (key fields):**
```python
class Asset(models.Model):
    asset_number = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=300)
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT)
    manufacturer = models.CharField(max_length=200, blank=True)
    status = models.CharField(choices=STATUS_CHOICES, default='ACTIVE')
    condition = models.CharField(choices=CONDITION_CHOICES, default='GOOD')
    acquisition_cost = models.DecimalField(max_digits=15, decimal_places=2)
    org_unit_name = models.CharField(max_length=200, blank=True)
    asset_expiry_date = models.DateField(null=True, blank=True)
```

**Helper properties:**
```python
@property
def is_expired(self):
    return self.asset_expiry_date < timezone.now().date()

@property
def expires_soon(self):
    days_left = (self.asset_expiry_date - timezone.now().date()).days
    return 0 <= days_left <= 90
```

<a name="15-19"></a>
### 15.19 `assets/api_views.py` — Asset API (628 lines)

**Why it exists:** REST API for the Flutter app to manage assets.

**Who imports it:** `authentication/api_urls.py`.

**Classes:**

**AssetListCreateAPIView:**
- GET: List assets with filters (search, status, category, condition) + pagination
- POST: Create asset with auto-generated asset number + audit log

**AssetDetailAPIView:**
- GET: Single asset details
- PUT: Update with field-level old/new audit
- DELETE: Delete (Ministry Admin only) + audit

**Key — auto-generated asset numbers:**
```python
def generate_asset_number(self, schema_name, category_code):
    # Format: MOH-ICT-2025-0001
    prefix = schema_name.replace('_schema', '').upper()[:3]
    year = str(timezone.now().year)
    base = f"{prefix}-{category_code}-{year}-"
    # Find highest existing number and increment
```

**Key — update with field-level audit:**
```python
def put(self, request, asset_id):
    old_value = {'name': asset.name, 'status': asset.status}
    # Update fields
    new_value = {'name': asset.name, 'status': asset.status}
    AuditLog.objects.create(action='UPDATE', old_value=old_value, new_value=new_value)
```

<a name="15-20"></a>
### 15.20 `assets/views.py` — Asset Web Pages (577 lines)

**Why it exists:** Browser-based pages for managing assets.

**Who imports it:** `config/urls.py`.

**Functions:**
- `asset_list_view` — Table with filters, search, pagination
- `asset_create_view` — Form to create asset
- `asset_detail_view` — Single asset details
- `asset_edit_view` — Edit form with old/new audit
- `asset_delete_view` — POST-only delete

<a name="15-21"></a>
### 15.21 `organizations/models.py` — Org, Master Data, Audit (230 lines)

**Why it exists:** Three critical models — OrgUnit, MasterData, AuditLog.

**Who imports it:** `organizations/views.py`, `organizations/api_views.py`.

**OrgUnit — Organisation Hierarchy:**
```python
class OrgUnit(models.Model):
    UNIT_TYPES = [('MINISTRY', 'Ministry'), ('AGENCY', 'Agency'), ('FACILITY', 'Facility')]
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    unit_type = models.CharField(choices=UNIT_TYPES)
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True)
```

**MasterData — Reference Data:**
```python
CATEGORIES = ['FUNDING_SOURCE', 'ACQUISITION_METHOD', 'LOCATION_TYPE', 'DISPOSAL_METHOD', 'COST_CENTRE']
```

**AuditLog — Immutable Record:**
```python
class AuditLog(models.Model):
    def save(self, *args, **kwargs):
        if self.pk is not None:  # Already exists
            raise PermissionError("Cannot modify audit log!")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Cannot delete audit log!")
```

<a name="15-22"></a>
### 15.22 `organizations/views.py` — Org + Audit Web Pages (403 lines)

**Why it exists:** Browser pages for org hierarchy and audit logs.

**Pages:**
- `/organisation/` — Tree: Ministry → Agencies → Facilities
- `/organisation/create/` — Add agency/facility
- `/audit-logs/` — Paginated log with action filter

<a name="15-23"></a>
### 15.23 `organizations/api_views.py` — Org + Dashboard API (424 lines)

**Why it exists:** API for org hierarchy, audit logs, dashboard stats.

**Endpoints:**

**OrgUnitListAPIView (GET /api/org-units/):**
Returns full tree + flat list of facilities for Flutter dropdowns.

**AuditLogListAPIView (GET /api/audit-logs/):**
Paginated audit logs with action/model filters.

**DashboardStatsAPIView (GET /api/dashboard/stats/):**
- Super Admin: counts across all ministries
- Ministry user: counts, expiry warnings, recent audit

<a name="15-24"></a>
### 15.24 `organizations/master_data_views.py` — Reference Data (589 lines)

**Why it exists:** Web pages for managing reference lists.

**Pages:**
- `/master-data/` — List entries grouped by category
- `/master-data/create/` — Add new entry
- `/master-data/seed/` — Seed 35 default entries
- `/master-data/categories/` — Manage asset categories

<a name="15-25"></a>
### 15.25 `tenants/models.py` — Ministry Blueprint (47 lines)

**Why it exists:** Defines the Ministry and Domain models.

```python
class Ministry(TenantMixin):
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    auto_create_schema = True  # Creates PG schema automatically!
```

The `auto_create_schema = True` is the magic. Saving a Ministry automatically runs `CREATE SCHEMA` and creates all tenant tables inside it.

<a name="15-26"></a>
### 15.26 `tenants/views.py` — Ministry Management (261 lines)

**Why it exists:** Super Admin pages for managing ministries.

**Pages:**
- `/ministries/` — List all ministries
- `/ministries/create/` — Create new ministry (validates schema, creates DB schema + domain + root OrgUnit)
- `/ministries/5/` — Ministry details
- `/ministries/5/toggle/` — Activate/deactivate

<a name="15-27"></a>
### 15.27 `authentication/management/commands/setup_demo_data.py` (553 lines)

**Why it exists:** One command to clean test data and seed professional demo data.

**Usage:** `python manage.py setup_demo_data`

**What it does:**
1. Clean: Deletes LoginAttempt, PendingAccess, all Assets and AuditLogs
2. Seed MOH (9 assets): Dell Laptop TSh 2.85M, Toyota Land Cruiser TSh 85M, medical equipment, etc.
3. Seed MOF (4 assets): HP EliteBook TSh 3.1M, Toyota Fortuner TSh 78M, etc.
4. Create audit log entries

<a name="15-28"></a>
### 15.28 Templates Directory

```
templates/
├── shared/
│   ├── base.html             ← Main layout (all pages extend this)
│   └── pagination.html       ← Page number buttons
├── dashboard/dashboard.html
├── authentication/
│   ├── login.html
│   ├── user_form.html, user_list.html, user_edit.html, user_reset_password.html
│   └── pending_access_list.html, pending_access_review.html
├── assets/
│   ├── asset_list.html, asset_form.html, asset_detail.html
├── organizations/
│   ├── org_unit_list.html, org_unit_form.html, org_unit_edit.html
│   ├── master_data_list.html, master_data_form.html, master_data_edit.html
│   ├── asset_category_list.html, asset_category_form.html, asset_category_edit.html
│   └── audit_log.html
└── tenants/
    ├── ministry_list.html, ministry_form.html, ministry_detail.html
```

<a name="15-29"></a>
### 15.29 File Dependency Diagram

```
manage.py
    │
    └── config/settings.py  (loaded at startup)
            │
            ├── config/urls.py  (reads URL patterns)
            │       │
            │       ├── authentication/views.py       (login, logout)
            │       ├── authentication/dashboard_views.py
            │       ├── authentication/user_views.py
            │       ├── authentication/pending_access_views.py
            │       ├── assets/views.py
            │       ├── organizations/views.py
            │       ├── organizations/master_data_views.py
            │       ├── tenants/views.py
            │       └── authentication/api_urls.py
            │               │
            │               ├── authentication/api_views.py
            │               │       └── authentication/api_serializers.py
            │               │       └── authentication/models.py
            │               │       └── organizations/models.py (AuditLog)
            │               │
            │               ├── assets/api_views.py
            │               │       └── assets/models.py
            │               │
            │               └── organizations/api_views.py
            │                       └── organizations/models.py
            │
            ├── authentication/middleware.py  (SchemaMiddleware)
            ├── authentication/oidc_backend.py  (Keycloak bridge)
            └── authentication/keycloak_admin.py  (Keycloak API calls)
```

---

<a name="ch-16"></a>
## CHAPTER 16: COMMON PANEL QUESTIONS

<a name="16-1"></a>
### 16.1 Architecture & Design (30 questions)

**Q1: What problem does this system solve?**
A: It solves the problem of lost and untracked government assets. Before this system, ministries tracked assets on paper and Excel sheets — records were lost, expired equipment stayed in use, and auditors could not verify inventory. This platform provides a digital, searchable, tamper-proof record of every government asset from acquisition to disposal.

**Q2: Why did you choose Django for this project?**
A: Django is the most popular Python web framework for government systems. It comes with built-in security features (CSRF protection, XSS prevention, SQL injection prevention), an ORM for database management, authentication system, and admin panel. It is well-documented, has a large community, and is suitable for data-intensive applications like asset management.

**Q3: Why PostgreSQL over MySQL?**
A: PostgreSQL supports schemas — a feature that lets us split a single database into separate sections for each ministry. MySQL does not have this feature. Since our multi-tenancy depends on schema isolation, PostgreSQL was the only choice.

**Q4: What is django-tenants and why do you use it?**
A: django-tenants is a Django package that enables multi-tenancy using PostgreSQL schemas. When a new ministry is created, it automatically creates a new schema and runs migrations inside it. It also provides the schema_context() function that lets us switch between schemas in code.

**Q5: How does multi-tenancy work at the database level?**
A: Each ministry gets their own PostgreSQL schema (like a folder). User accounts are in a shared "public" schema. Assets, organizations, and audit logs are in each ministry's private schema. When a query runs, `SET search_path = moh_schema` is added, so PostgreSQL only looks in that schema. Other ministries' data is completely invisible.

**Q6: How many ministries can this support?**
A: PostgreSQL supports thousands of schemas without performance degradation. The architecture is designed for the ~26 Tanzanian government ministries plus agencies. Each schema is independent — adding a new one does not affect existing ones.

**Q7: How do you handle schema migrations when you add a new field?**
A: Use `python manage.py makemigrations` to generate migration files, then `python manage.py migrate_schemas` to apply them to ALL schemas (public + all ministry schemas). django-tenants handles this automatically.

**Q8: Can you add a new ministry without downtime?**
A: Yes. The Super Admin fills a form, clicks save, and a new schema is created instantly. Other ministries continue working unaffected. Zero downtime.

**Q9: How does the system handle concurrent users?**
A: In development, the built-in server handles one request at a time. In production, Gunicorn runs multiple Django worker processes, each handling one request. Multiple users can be served simultaneously. PostgreSQL also handles concurrent connections efficiently.

**Q10: What is the difference between the web version and the mobile app?**
A: The web version uses Keycloak SSO for login and returns HTML pages for browser viewing. The mobile app uses direct API login (JWT tokens) and returns JSON data for the Flutter app to render. Both access the same data and use the same permissions — only the interface differs.

**Q11: How does the system handle file uploads (asset photos)?**
A: The Asset model has a `photo = ImageField(upload_to='assets/photos/')` field. Uploaded photos are stored in the `media/` directory. In development, Django serves them via the `static()` URL helper. In production, Nginx would serve them directly.

**Q12: How is asset numbering handled?**
A: Asset numbers are auto-generated in the format `MOH-ICT-2025-0001` — ministry prefix, category code, year, and a zero-padded sequence number. The code finds the highest existing sequence and increments it, ensuring uniqueness.

**Q13: How does search work?**
A: The API supports filtering by search term (matches name and asset_number), status, category code, and condition. The web version uses the same filters plus a more detailed search form. Both use Django's ORM `__icontains` for case-insensitive partial matching.

**Q14: What happens when you delete an asset?**
A: Only Ministry Admin or Super Admin can delete. Before deletion, an audit log entry is created recording who deleted it and when. The deletion is permanent. For normal operations, assets should be marked as DISPOSED rather than deleted.

**Q15: How are asset categories managed?**
A: Each ministry manages their own categories. Categories are classified by code (ICT, VEH, FURN, MED). Ministry Admins can add, edit, or deactivate categories through the web interface.

<a name="16-2"></a>
### 16.2 Security Questions (30 questions)

**Q16: What security measures have you implemented?**
A: Nine measures: (1) Keycloak SSO — passwords never handled by us, (2) Role-based access — 5 roles with different permissions, (3) Brute-force lockout — 5 attempts then 15-min lock, (4) Immutable audit log — no editing or deleting, (5) JWT token security — 30-min expiry, rotation, blacklisting, (6) Pending access approval — no auto-created accounts, (7) Dual logging — database + file, (8) Security headers — XSS, clickjacking, MIME protection, (9) Schema isolation — database-level ministry separation.

**Q17: How does brute-force protection work?**
A: Every failed login increments a counter per username + IP address. After 5 failures, the account is locked for 15 minutes (locked_until = now + 15 minutes). Successful login resets the counter. Locked users get HTTP 429 with the remaining lockout time displayed.

**Q18: Why is the audit log immutable?**
A: The AuditLog model overrides save() and delete() to prevent changes to existing records. If code tries to modify or delete an audit entry, Django raises PermissionError. This makes the audit log legally admissible as evidence.

**Q19: How does Keycloak SSO protect passwords?**
A: Users type their password into Keycloak's page, NOT Django's page. Django never sees the password. If our Django server is breached, the attacker still cannot steal passwords because we never had them. Keycloak handles password storage with industry-standard hashing.

**Q20: What happens if someone steals a JWT token?**
A: Access tokens expire in 30 minutes, limiting the damage window. Refresh tokens can be blacklisted when used. Additionally, token rotation ensures old refresh tokens stop working once new ones are issued.

**Q21: Can a user access another ministry's data through the API?**
A: No. Two layers of protection: (1) The user's role and ministry_schema determine what data they can access at the application level. (2) The database schema isolation means queries literally run in a different schema — MOH queries go to moh_schema, not mof_schema.

**Q22: How is the SECRET_KEY protected?**
A: The SECRET_KEY is stored in .env, which is listed in .gitignore. It is never committed to version control. In production, it would be set through environment variables or a secrets manager.

**Q23: How do you prevent SQL injection?**
A: Django's ORM automatically parameterizes all queries. User input is passed as parameters, not concatenated into SQL strings. We never write raw SQL queries. This prevents SQL injection by design.

**Q24: How do you protect against XSS attacks?**
A: Django's template engine automatically escapes HTML in all variables. User input displayed as `{{ asset.name }}` has HTML characters escaped. We also set `SECURE_BROWSER_XSS_FILTER = True` to enable the browser's built-in XSS filter.

**Q25: How do you prevent CSRF attacks?**
A: Django's CSRF middleware adds a CSRF token to every form. Without a valid token, POST/PUT/DELETE requests are rejected. API endpoints use JWT Bearer tokens instead.

**Q26: How does CORS work in this project?**
A: The `django-cors-headers` middleware adds CORS headers to responses. In development, `CORS_ALLOW_ALL_ORIGINS = True` allows any origin (including the Flutter app). In production, this would be restricted to specific domains.

**Q27: What is stored in the security log vs the audit log?**
A: The security log (logs/security.log) is a text file for real-time monitoring — login successes, failures, blocks. The audit log (database table) is a permanent, tamper-proof record of every action performed in the system.

**Q28: How do you handle account lockout for Keycloak users?**
A: Keycloak has its own brute-force detection that can be enabled separately. Our Django-level brute-force protection applies to API login. For web users, Keycloak handles lockout independently.

**Q29: What happens if the database connection fails?**
A: Django raises an OperationalError. The view returns a 500 error. The error is logged to django.log. The development server continues running and will try again on the next request. In production, the server process might restart.

**Q30: How do you handle session timeout?**
A: `SESSION_COOKIE_AGE = 7200` (2 hours). After 2 hours of inactivity, the session expires. `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` also ends the session when the browser is closed.

<a name="16-3"></a>
### 16.3 Authentication & Authorization Questions (20 questions)

**Q31: What is the difference between authentication and authorization?**
A: Authentication proves who you are (login). Authorization determines what you can do (permissions). Authentication happens first — prove identity, then check permissions. Keycloak handles authentication. Our decorators and permission classes handle authorization.

**Q32: What are the five user roles?**
A: SUPER_ADMIN (platform-wide), MINISTRY_ADMIN (one ministry), AGENCY_MANAGER (agency level), FACILITY_CLERK (facility level), AUDITOR (read-only). Each role has specific permissions.

**Q33: How do roles restrict access to web pages?**
A: Through the `@role_required()` decorator. For example, `@role_required('SUPER_ADMIN')` on a view blocks anyone except SUPER_ADMIN, redirecting them to the dashboard with an error message.

**Q34: How do roles restrict access to API endpoints?**
A: Through DRF permission classes. Each endpoint specifies its required permission. For example, `CanDeleteAssets` only allows SUPER_ADMIN and MINISTRY_ADMIN to send DELETE requests.

**Q35: What is the difference between a decorator and a permission class?**
A: Decorators are Python functions that wrap web view functions. They run before the view runs. Permission classes are DRF classes that check permissions for API views. Decorators check roles for web pages. Permission classes check roles for API endpoints.

**Q36: How does the OIDC backend find a user?**
A: `filter_users_by_claims()` first tries to find the user by keycloak_id (from the token's "sub" claim). If not found, it tries by username (from "preferred_username" claim). If found by username but keycloak_id is missing, it links them.

**Q37: Why not auto-create users in create_user()?**
A: Security. Auto-creation would let anyone with a Keycloak account access our system. Instead, we create a PendingAccess record that requires admin approval. Every access must be explicitly granted.

**Q38: How are roles synchronized between Keycloak and Django?**
A: When a user logs in via SSO, `update_user()` in the OIDC backend reads the role and ministry_schema from the Keycloak token attributes and updates the Django user record. They are kept in sync on every login.

**Q39: What happens if a user's role changes in Keycloak?**
A: The next time they log in via SSO, `update_user()` detects the change and updates Django's record. Changes take effect on the next SSO login.

**Q40: How does ministry_isolation_check work?**
A: It ensures the user has a `ministry_schema` field set (except Super Admin, who operates at platform level). If a user tries to view a ministry page without a schema assignment, they are redirected to login with an error.

<a name="16-4"></a>
### 16.4 Technical Questions (30 questions)

**Q41: What is JWT?**
A: JSON Web Token — a digital ID card with a cryptographic signature. It contains user information (role, ministry) and is signed so it cannot be tampered with. It has an expiration time. It is used for API authentication.

**Q42: What is the difference between access token and refresh token?**
A: Access token lasts 30 minutes and is used to access data. Refresh token lasts 1 day and can ONLY be used to get new access tokens. This limits damage if a token is stolen while providing good UX.

**Q43: What is token rotation?**
A: When you use a refresh token to get new tokens, you receive a NEW refresh token. The old one is blacklisted. This prevents replay attacks — a stolen refresh token can only be used once.

**Q44: What is blacklisting?**
A: The system maintains a list of blacklisted refresh tokens. Any blacklisted token is rejected, even if its signature is valid. This allows us to revoke tokens that have been used (rotation) or explicitly logged out.

**Q45: How many requests can the system handle?**
A: In development with `runserver`, one request at a time. In production with Gunicorn (4 workers), 4 simultaneous requests. With Nginx load balancing, many more. PostgreSQL handles hundreds of concurrent connections.

**Q46: How is the system tested?**
A: Through automated tests in `tests.py` files (using pytest-django). Tests cover models, views, API endpoints, and permissions. Run with `python manage.py test`.

**Q47: How do you set up the project on a new machine?**
A: Install Python, PostgreSQL, and Keycloak. Clone the project. Create a virtual environment. Install requirements. Create the database. Run migrations. Create a superuser. Create ministries. Seed demo data. Start the server.

**Q48: What commands do you use daily?**
A: `python manage.py runserver`, `python manage.py setup_demo_data`, `kc.bat start-dev --http-port=8180`, `flutter run`.

**Q49: How do you back up the database?**
A: `pg_dump -U postgres government_assets_db > backup.sql`. This creates a complete backup including all schemas and data. Restore with `psql -U postgres government_assets_db < backup.sql`.

**Q50: How do you add a new field to the Asset model?**
A: Add the field to `Asset` in `assets/models.py`. Run `python manage.py makemigrations assets`. Run `python manage.py migrate_schemas`. The field is added to ALL ministry schemas.

**Q51: How does the system handle different currencies?**
A: Currently, all financial fields are in Tanzanian Shillings (TZS) as shown in the demo data. There is no multi-currency support built in.

**Q52: How do you handle asset depreciation?**
A: The Asset model has `current_value` and `useful_life_years` fields. The system stores these values but does not automatically calculate depreciation. This is a data entry field.

**Q53: How does the system handle asset disposal?**
A: Assets can be marked as status='DISPOSED' with disposal_method, disposal_date, and disposal_notes fields. The complete disposal record is preserved.

**Q54: How do you search across multiple fields?**
A: The API builds a Q object: `Q(name__icontains=search) | Q(asset_number__icontains=search)`. This searches both name and asset_number with a single query.

**Q55: How does pagination work?**
A: The `paginate_queryset()` helper creates a Paginator with 20 items per page. The view returns count, total_pages, current_page, and the items for the current page. The Flutter app uses current_page to fetch the next page.

**Q56: What happens if you request a non-existent asset?**
A: `get_object_or_404` returns HTTP 404. The user sees a "Not found" error.

**Q57: How does the system handle concurrent updates to the same asset?**
A: The last PUT request wins. There is no optimistic locking. If two users edit the same asset simultaneously, the last one to save overwrites the first one's changes.

**Q58: How do you reset the database to a clean state?**
A: `python manage.py setup_demo_data --clean` deletes all test data. To fully reset: drop and recreate the database, run migrations, then setup_demo_data.

**Q59: How do you monitor the system?**
A: Currently through log files (django.log, security.log). In production, monitoring tools like Sentry or Prometheus would be added.

**Q60: What is the most complex part of the codebase?**
A: The multi-tenant architecture. Ensuring that every query correctly switches to the right schema, that users can only access their own ministry's data, and that migrations apply to all schemas correctly. The asset API with filtering, pagination, and field-level audit logging is also complex.

<a name="16-5"></a>
### 16.5 Deployment & Operations Questions (20 questions)

**Q61: How would you deploy this to production?**
A: Use Gunicorn as the WSGI server behind Nginx as a reverse proxy. Set DEBUG=False. Lock down ALLOWED_HOSTS. Enable HTTPS with SSL certificate. Configure proper logging. Set up database backups. Use environment variables for secrets.

**Q62: What is Nginx and why is it needed?**
A: Nginx is a web server optimized for serving static files and handling many concurrent connections. It acts as a reverse proxy — it receives client requests, serves static files directly (fast), and forwards dynamic requests to Gunicorn. It also handles HTTPS, rate limiting, and load balancing.

**Q63: What is Gunicorn?**
A: Gunicorn is a WSGI server that runs Django in production. Unlike Django's development server (single process, single thread), Gunicorn runs multiple worker processes that can handle requests simultaneously.

**Q64: How would you scale this system?**
A: Vertically: increase server RAM/CPU. Horizontally: add more Gunicorn workers, add more Nginx servers behind a load balancer, add database read replicas. Each Django instance is stateless (sessions can use Redis), so horizontal scaling is straightforward.

**Q65: How do you manage environment-specific configuration?**
A: Through the .env file. Different environments (development, staging, production) have different .env files with appropriate values. The .env is never committed to version control.

**Q66: How do you handle secrets in production?**
A: Secrets (SECRET_KEY, DB_PASSWORD, KEYCLOAK_CLIENT_SECRET) are stored in environment variables on the server, not in files. A secrets manager (like HashiCorp Vault or AWS Secrets Manager) could be used for added security.

**Q67: How do you ensure zero-downtime deployments?**
A: Use Gunicorn with graceful reload (`kill -HUP`). New workers start while old workers finish existing requests. No downtime during code updates as long as database migrations are backward-compatible.

**Q68: How do you handle database migrations in production?**
A: Run `python manage.py migrate_schemas` during a maintenance window or between deployment steps. Ensure backward compatibility — deploy code that works with both old and new schema, then run migrations, then deploy code that requires the new schema.

**Q69: How do you monitor errors in production?**
A: Through log files and potentially error monitoring services like Sentry. Django's logging configuration sends errors to files. In production, alerts can be configured based on log patterns.

**Q70: How do you back up the Keycloak database?**
A: Keycloak uses an embedded H2 database by default (in dev mode). Backup involves copying the Keycloak data directory. For production, Keycloak should use an external database (PostgreSQL) that can be backed up normally.

<a name="16-6"></a>
### 16.6 Testing Questions (10 questions)

**Q71: How do you test the API?**
A: Through Swagger UI at /api/docs/ (interactive testing), Postman (collections), or automated tests (pytest-django). The automated tests use Django's test client to simulate API requests and verify responses.

**Q72: What is the difference between unit tests and integration tests?**
A: Unit tests test one component in isolation (e.g., a single function). Integration tests test multiple components together (e.g., the full login flow). Our project has both types in the tests.py files.

**Q73: How do you test multi-tenancy?**
A: Automated tests create tenant schemas, create users in different schemas, and verify that data is isolated. Tests confirm that a user in moh_schema cannot access data in mof_schema.

**Q74: How do you test the brute-force protection?**
A: Tests send multiple failed login requests, verify that after 5 attempts the account is locked, and verify that a 429 status code is returned with the correct lockout message.

**Q75: How do you test the audit log immutability?**
A: Tests attempt to modify or delete an existing audit log entry and verify that PermissionError is raised. Tests also verify that creating a new audit entry succeeds.

---

<a name="ch-17"></a>
## CHAPTER 17: COMMON BEGINNER CONFUSIONS

<a name="17-1"></a>
### 17.1 API vs. Website

| Concept | Website | API |
|---------|---------|-----|
| Returns | HTML (visual page) | JSON (structured data) |
| Read by | Humans in browser | Programs (mobile apps, other servers) |
| URL example | `/assets/` | `/api/assets/` |
| Authentication | Session cookie | JWT Bearer token |
| Think of | A restaurant menu | A food delivery API for robots |

**Truth:** They run on the same server, share the same database, often share the same logic. They just format the output differently.

<a name="17-2"></a>
### 17.2 Browser vs. Client

**Misconception:** "A client is a person using the system."
**Truth:** In software, a "client" is any program that makes requests. The browser is a client. The Flutter app is a client. Another government server is a client. The user is the PERSON operating the client.

<a name="17-3"></a>
### 17.3 JWT vs. Login

**Misconception:** "JWT is the login system."
**Truth:** JWT is the OUTPUT of a successful login. The LOGIN is the process of verifying credentials (username + password). The JWT is the TOKEN you receive after successful login so you don't need to send your password on every request.

<a name="17-4"></a>
### 17.4 Token vs. Password

**Misconception:** "A JWT token is like a password."
**Truth:** A password is a SECRET you know. A JWT token is a TEMPORARY PASS. A password can be used forever (until changed). A JWT expires in 30 minutes. A password is sent once during login. A JWT is sent on every request.

<a name="17-5"></a>
### 17.5 API Key vs. JWT

**Misconception:** "A JWT is the same as an API key."
**Truth:** An API key is a static, permanent identifier for a program (like a service account password). A JWT is a temporary, user-specific token that contains information about the user (role, ministry). API keys don't expire. JWTs expire.

<a name="17-6"></a>
### 17.6 Swagger vs. API

**Misconception:** "Swagger IS the API."
**Truth:** Swagger is DOCUMENTATION of the API. The API is the actual endpoints that return data. Swagger just reads the code and displays what the API does. You can use Swagger to TEST the API, but Swagger is not the API itself.

<a name="17-7"></a>
### 17.7 JSON vs. Database

**Misconception:** "JSON is stored in the database."
**Truth:** JSON is a FORMAT for transmitting data between systems. The database stores data in TABLES (rows and columns). When the API sends data, it converts from tables to JSON. When it receives data, it converts from JSON back to tables.

<a name="17-8"></a>
### 17.8 Django vs. PostgreSQL

**Misconception:** "Django is the database."
**Truth:** Django is the WEB FRAMEWORK (handles requests, runs code, renders pages). PostgreSQL is the DATABASE (stores data). Django CONNECTS to PostgreSQL. They are separate programs. You can replace PostgreSQL with another database without changing most Django code.

<a name="17-9"></a>
### 17.9 Backend vs. Server

**Misconception:** "The backend is the server."
**Truth:** The SERVER is the physical or virtual computer. The BACKEND is the CODE that runs on it. The server is hardware (or a VM). The backend is software (Django, our Python code). You can have multiple backends on one server.

<a name="17-10"></a>
### 17.10 Endpoint vs. URL

**Misconception:** "Every URL is an endpoint."
**Truth:** An ENDPOINT is a specific URL that connects to a specific function in the code. Not every URL is an endpoint — only the URLs listed in `urls.py` that lead to view functions. A URL like `/some-random-page/` is a URL but not an endpoint.

<a name="17-11"></a>
### 17.11 Authentication vs. Authorization

**Misconception:** "They are the same thing."
**Truth:** Authentication = "Who are you?" (proving identity). Authorization = "What can you do?" (checking permissions). They are completely different. A user can be authenticated (they have a valid login) but not authorized (they don't have permission for a specific action).

<a name="17-12"></a>
### 17.12 Keycloak Login vs. Django Login

**Misconception:** "They are competing login systems."
**Truth:** They work TOGETHER. Keycloak checks the password (authentication). Django finds the user and creates a session (user management). Keycloak says "this password is correct." Django says "I know this user, here's their session."

<a name="17-13"></a>
### 17.13 Refresh Token vs. Access Token

**Misconception:** "They are the same thing."
**Truth:** An access token can access data (call APIs). A refresh token can ONLY get new access tokens. The refresh token cannot call a single API endpoint. It has one job: to be exchanged for new access tokens.

<a name="17-14"></a>
### 17.14 Session vs. JWT

**Misconception:** "Sessions and JWTs are interchangeable."
**Truth:** Sessions store data ON THE SERVER. JWTs store data IN THE TOKEN. Sessions are stateful (server remembers you). JWTs are stateless (token contains everything). Sessions can be revoked instantly. JWTs cannot be revoked (must wait for expiry).

<a name="17-15"></a>
### 17.15 User Account vs. Identity Provider

**Misconception:** "Keycloak IS the user account."
**Truth:** Keycloak is the IDENTITY PROVIDER (checks passwords). Django has the USER ACCOUNT (stores role, ministry, permissions). They are separate. The same person exists in both systems but for different purposes.

<a name="17-16"></a>
### 17.16 Frontend vs. Backend

**Misconception:** "Frontend is the design, backend is the logic."
**Truth:** Frontend = what the user SEES and INTERACTS WITH (HTML pages, Flutter app). Backend = the CODE THAT RUNS ON THE SERVER (Django views, models, APIs). Frontend makes requests. Backend processes them and returns responses.

<a name="17-17"></a>
### 17.17 GET vs. POST

**Misconception:** "GET and POST are interchangeable."
**Truth:** GET = requesting data (should never change anything). POST = creating something new (changes data). If you use GET to delete an asset, a browser pre-fetching pages could accidentally delete everything. Use GET for safe operations, POST/PUT/DELETE for changes.

<a name="17-18"></a>
### 17.18 401 vs. 403

**Misconception:** "They both mean access denied."
**Truth:** 401 = "UNAUTHORIZED — you are not logged in. Log in and try again." 403 = "FORBIDDEN — you are logged in but you don't have permission for this specific action." 401 means provide credentials. 403 means your credentials don't grant access.

<a name="17-19"></a>
### 17.19 Production vs. Development

**Misconception:** "They should behave the same."
**Truth:** Development prioritizes convenience (detailed errors, automatic reload, relaxed security). Production prioritizes security and performance (no detailed errors, HTTPS, caching, multiple workers). What works in dev might not work in prod and vice versa.

<a name="17-20"></a>
### 17.20 Code vs. Configuration

**Misconception:** "Everything is in the code."
**Truth:** Some things are CODE (logic, behavior) and some are CONFIGURATION (settings, secrets, environment). Code changes require redeployment. Configuration changes can often be made without redeployment (changing a .env file and restarting).

---

<a name="ch-18"></a>
## CHAPTER 18: VISUAL LEARNING — ASCII DIAGRAMS

<a name="18-1"></a>
### 18.1 System Architecture Overview

```
                          USERS
                            │
              ┌─────────────┼─────────────┐
              │             │             │
          Browser        Phone       Other System
              │             │             │
              │             │             │
         ┌────┴─────┐  ┌───┴───┐   ┌────┴────┐
         │ Keycloak │  │Flutter│   │ Python  │
         │ Port 8180│  │ App  │   │ Script  │
         └────┬─────┘  └───┬───┘   └────┬────┘
              │             │             │
              └──────┬──────┴──────┬──────┘
                     │             │
                     ▼             ▼
              ┌───────────────────────────┐
              │       DJANGO (Port 8000)   │
              │                           │
              │  ┌─────────────────────┐  │
              │  │   URL Router        │  │
              │  │   (config/urls.py)  │  │
              │  └──────────┬──────────┘  │
              │             │             │
              │  ┌──────────▼──────────┐  │
              │  │     Middleware × 11   │  │
              │  └──────────┬──────────┘  │
              │             │             │
              │  ┌──────────▼──────────┐  │
              │  │       Views          │  │
              │  │  (Web + API)         │  │
              │  └──────────┬──────────┘  │
              │             │             │
              │  ┌──────────▼──────────┐  │
              │  │      Models + ORM    │  │
              │  └──────────┬──────────┘  │
              └─────────────┼─────────────┘
                            │
                            ▼
              ┌───────────────────────────┐
              │    PostgreSQL (Port 5432)  │
              │                           │
              │  public schema (shared)   │
              │  moh_schema (MOH only)    │
              │  mof_schema (MOF only)    │
              └───────────────────────────┘
```

<a name="18-2"></a>
### 18.2 Request Flow (Web Login via Keycloak)

```
BROWSER              KEYCLOAK              DJANGO              DATABASE
  │                     │                    │                    │
  │ 1. GET /login/      │                    │                    │
  │─────────────────────┼───────────────────→│                    │
  │                     │                    │                    │
  │ 2. Login page       │                    │                    │
  │←────────────────────┼───────────────────│                    │
  │                     │                    │                    │
  │ 3. Click SSO button │                    │                    │
  │─────────────────────┼───────────────────→│                    │
  │                     │                    │                    │
  │ 4. Redirect to      │                    │                    │
  │    Keycloak         │                    │                    │
  │←────────────────────┼───────────────────│                    │
  │                     │                    │                    │
  │ 5. Enter password   │                    │                    │
  │─────────────────────→│                    │                    │
  │                     │ 6. Verify pwd      │                    │
  │                     │ ✓ Correct          │                    │
  │                     │                    │                    │
  │ 7. Redirect with    │                    │                    │
  │    auth code        │                    │                    │
  │←────────────────────┼───────────────────│                    │
  │                     │                    │                    │
  │ 8. /oidc/callback/  │                    │                    │
  │    with code        │                    │                    │
  │─────────────────────┼───────────────────→│                    │
  │                     │                    │                    │
  │                     │ 9. Exchange code   │                    │
  │                     │    for token       │                    │
  │                     │←──────────────────→│                    │
  │                     │                    │                    │
  │                     │                    │ 10. Find user      │
  │                     │                    │──────────────────→│
  │                     │                    │←──User found─────│
  │                     │                    │                    │
  │                     │                    │ 11. Create session │
  │                     │                    │                    │
  │ 12. Dashboard       │                    │                    │
  │←────────────────────┼───────────────────│                    │
```

<a name="18-3"></a>
### 18.3 Request Flow (Mobile API Login)

```
FLUTTER APP                            DJANGO                      DATABASE
    │                                     │                          │
    │ 1. POST /api/auth/login/            │                          │
    │    username + password              │                          │
    │────────────────────────────────────→│                          │
    │                                     │ 2. Check brute-force    │
    │                                     │    LoginAttempt table   │
    │                                     │─────────────────────────→│
    │                                     │←──Not locked───────────│
    │                                     │                          │
    │                                     │ 3. Validate credentials │
    │                                     │    authenticate()       │
    │                                     │─────────────────────────→│
    │                                     │                          │
    │                                     │ 4. If FAILED:           │
    │                                     │    Record attempt       │
    │                                     │    If >= 5: lock account│
    │                                     │─────────────────────────→│
    │                                     │                          │
    │                                     │ 5. If SUCCESS:          │
    │                                     │    Clear failed attempts│
    │                                     │    Generate JWT token   │
    │                                     │    Record audit log     │
    │                                     │─────────────────────────→│
    │                                     │                          │
    │ 6. Return JWT + user                │                          │
    │←────────────────────────────────────│                          │
    │                                     │                          │
    │ 7. Store token in secure storage    │                          │
    │                                     │                          │
    │ 8. GET /api/assets/                 │                          │
    │    Authorization: Bearer <token>    │                          │
    │────────────────────────────────────→│                          │
    │                                     │ 9. Verify JWT signature │
    │                                     │ 10. Switch to moh_schema│
    │                                     │ 11. Query assets        │
    │                                     │─────────────────────────→│
    │                                     │←──Results──────────────│
    │                                     │                          │
    │ 12. JSON asset list                 │                          │
    │←────────────────────────────────────│                          │
```

<a name="18-4"></a>
### 18.4 Database Schema Diagram

```
DATABASE: government_assets_db
════════════════════════════════════════════════════════════════

PUBLIC SCHEMA (shared by all ministries)
─────────────────────────────────────────
┌─────────────────────────────────────┐
│  authentication_customuser           │
│  ┌────┬────────┬────────┬────────┐  │
│  │ id │username│  role  │schema  │  │
│  ├────┼────────┼────────┼────────┤  │
│  │ 1  │moh_adm │MIN_    │moh_sch │  │
│  │    │in      │ADMIN   │ema     │  │
│  ├────┼────────┼────────┼────────┤  │
│  │ 2  │mof_adm │MIN_    │mof_sch │  │
│  │    │in      │ADMIN   │ema     │  │
│  └────┴────────┴────────┴────────┘  │
├─────────────────────────────────────┤
│  tenants_ministry                    │
│  ┌────┬──────────┬──────────────┐   │
│  │ id │   name   │ schema_name  │   │
│  ├────┼──────────┼──────────────┤   │
│  │ 1  │Min of    │ moh_schema   │   │
│  │    │Health    │              │   │
│  ├────┼──────────┼──────────────┤   │
│  │ 2  │Min of    │ mof_schema   │   │
│  │    │Finance   │              │   │
│  └────┴──────────┴──────────────┘   │
└─────────────────────────────────────┘

MOH SCHEMA (Ministry of Health only)
─────────────────────────────────────
┌─────────────────────────────────────┐
│  assets_asset                       │
│  ┌────┬──────────┬────────┬──────┐  │
│  │ id │asset_num │  name  │status│  │
│  ├────┼──────────┼────────┼──────┤  │
│  │ 1  │MOH-ICT-  │Dell    │ACTIVE│  │
│  │    │2025-0001 │Laptop  │      │  │
│  ├────┼──────────┼────────┼──────┤  │
│  │ 2  │MOH-VEH-  │Toyota  │ACTIVE│  │
│  │    │2025-0001 │LC      │      │  │
│  └────┴──────────┴────────┴──────┘  │
├─────────────────────────────────────┤
│  organizations_auditlog              │
│  ┌────┬────────┬────────┬────────┐   │
│  │ id │ action │  user  │  time  │   │
│  ├────┼────────┼────────┼────────┤   │
│  │ 1  │ CREATE │  Amina │ 09:30  │   │
│  │ 2  │ LOGIN  │  Amina │ 09:31  │   │
│  └────┴────────┴────────┴────────┘   │
└─────────────────────────────────────┘

MOF SCHEMA (Ministry of Finance only)
─────────────────────────────────────
┌─────────────────────────────────────┐
│  assets_asset                       │
│  ┌────┬──────────┬────────┬──────┐  │
│  │ id │asset_num │  name  │status│  │
│  ├────┼──────────┼────────┼──────┤  │
│  │ 1  │MOF-ICT-  │HP      │ACTIVE│  │
│  │    │2025-0001 │EliteBk │      │  │
│  └────┴──────────┴────────┴──────┘  │
└─────────────────────────────────────┘
```

<a name="18-5"></a>
### 18.5 JWT Token Structure

```
┌─────────────────────────────────────────────────────────────────┐
│                         JWT TOKEN                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  HEADER (Base64 decoded)                                         │
│  ┌─────────────────────────────────────────────────────┐        │
│  │ {                                                  │        │
│  │   "alg": "HS256",       ← Algorithm used to sign  │        │
│  │   "typ": "JWT"          ← Type of token           │        │
│  │ }                                                  │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
│  PAYLOAD (Base64 decoded)                                        │
│  ┌─────────────────────────────────────────────────────┐        │
│  │ {                                                  │        │
│  │   "token_type": "access",  ← Is this access/refresh│        │
│  │   "exp": 1700000000,       ← Expiration timestamp  │        │
│  │   "iat": 1699998200,       ← Issued at timestamp   │        │
│  │   "jti": "abc123",         ← Unique token ID       │        │
│  │   "user_id": 1,            ← Which user            │        │
│  │   "role": "MINISTRY_ADMIN",  ← User's role         │        │
│  │   "ministry_schema": "moh_schema" ← User's schema  │        │
│  │ }                                                  │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
│  SIGNATURE (created by the server):                              │
│  HMAC-SHA256(                                                     │
│    base64(header) + "." + base64(payload),                        │
│    SECRET_KEY                                                     │
│  )                                                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

<a name="18-6"></a>
### 18.6 Middleware Pipeline

```
REQUEST IN
    │
    ▼
┌─────────────────────────────────────────────┐
│ TenantMainMiddleware                         │
│  Sets up database connection for schema     │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ SecurityMiddleware                           │
│  Adds security headers, HTTPS redirect      │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ SessionMiddleware                            │
│  Reads/sets session cookie                  │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ CorsMiddleware                               │
│  Adds CORS headers for cross-origin requests│
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ CommonMiddleware                             │
│  URL normalization, trailing slashes        │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ CsrfViewMiddleware                           │
│  CSRF token check for unsafe methods        │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ AuthenticationMiddleware                     │
│  Decodes JWT, sets request.user             │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ MessagesMiddleware                           │
│  Flash message framework                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ XFrameOptionsMiddleware                      │
│  Clickjacking protection                    │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ SchemaMiddleware (OUR CODE)                  │
│  Sets request.schema_name from user         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│ SessionRefresh (mozilla_django_oidc)        │
│  OIDC session check (web only)             │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
            VIEW FUNCTION
                  │
                  ▼
            RESPONSE OUT
```

---

<a name="ch-19"></a>
## CHAPTER 19: REAL GOVERNMENT EXAMPLES

<a name="19-1"></a>
### 19.1 Scenario 1: Dr. Amina Discovers an Expired Asset

```
DR. AMINA HASSAN — ICT Director, Ministry of Health

Situation: The Ministry of Health has a fire extinguisher in
           the radiology department that was bought in 2020.
           Fire extinguishers must be replaced every 5 years.
           It is now 2025.

Before the system:
  - The extinguisher stays on the wall
  - Nobody knows when it expires
  - If a fire happens, the extinguisher might not work
  - If the auditor inspects, the ministry gets in trouble

With our system:
  Step 1: Dr. Amina logs into the dashboard
          → Sees: "1 asset expired, 2 expiring within 30 days"
  Step 2: Clicks "Expired Assets"
          → Shows: Fire Extinguisher - Rad Dept - Expired 2025-03-15
  Step 3: Clicks the asset record
          → Shows: Purchase date, supplier, location, all details
  Step 4: Creates a disposal record (DISPOSED method = "Replaced")
  Step 5: Creates a new asset record for the replacement
  Step 6: Audit log now shows:
          "Amina Hassan DISPOSED Fire Extinguisher (old)"
          "Amina Hassan CREATED Fire Extinguisher (new)"
```

<a name="19-2"></a>
### 19.2 Scenario 2: Mr. Juma Onboards a New Ministry

```
MR. JUMA OMARY — System Administrator, President's Office

The government has created a new ministry: Ministry of Water.
They need access to the asset management platform.

Step 1: Mr. Juma logs in as Super Admin
Step 2: Goes to /ministries/create/
Step 3: Fills form:
        Name: "Ministry of Water"
        Short Name: "MOW"
        Schema: "mow_schema"
Step 4: Clicks Save
        → Django creates PostgreSQL schema: mow_schema
        → Runs migrations inside mow_schema
        → Creates Domain record: mow.localhost
        → Creates root OrgUnit of type MINISTRY
Step 5: System shows: "Ministry created successfully!"
Step 6: Mr. Juma creates user accounts for MOW staff
        → Username: mow_admin, Role: MINISTRY_ADMIN
        → Username: mow_clerk, Role: FACILITY_CLERK
Step 7: MOW staff can now log in and manage their assets
```

<a name="19-3"></a>
### 19.3 Scenario 3: Auditor Reviews Asset Records

```
MS. GRACE MPONDA — Government Auditor

It is annual audit time. Ms. Grace needs to verify that
all assets listed in the system actually exist.

Step 1: Grace logs in as AUDITOR (read-only)
Step 2: Goes to /audit-logs/
Step 3: Filters by date: "Last 12 months"
Step 4: Sees every CREATE, UPDATE, DELETE of assets
Step 5: Picks a sample:
        "MOH-ICT-2025-0001 — Dell Latitude 5440"
        CREATED by Amina Hassan on 2025-01-15
Step 6: Visits Radiology Department
        → Finds the Dell Latitude 5440
        → Checks serial number: MATCHES
Step 7: Confirms: "Asset exists, record is accurate"
Step 8: The audit log is immutable:
        → Nobody could have deleted or modified entries
        → Grace trusts the data completely
```

<a name="19-4"></a>
### 19.4 Scenario 4: Mobile Field Clerk Updates Asset

```
JOHN KAMAU — Facility Clerk at Muhimbili Hospital

John is at the hospital stores. A new delivery of 5 laptops arrived.
He needs to register them in the system.

Step 1: Opens Flutter app on his phone
Step 2: Logs in (JWT token received)
Step 3: Taps "Add Asset"
Step 4: Selects category: ICT Equipment
Step 5: Scans or types serial number
Step 6: Takes photo of the laptop
Step 7: Selects location: "ICT Department - Block B"
Step 8: Enters purchase details
Step 9: Taps "Save"
        → API call: POST /api/assets/
        → Django: auto-generates MOH-ICT-2025-0010
        → Django: records CREATE in audit log
        → Flutter: shows "Asset created successfully"
Step 10: John moves to the next laptop
```

<a name="19-5"></a>
### 19.5 Scenario 5: Finance Ministry Integrates

```
MINISTRY OF FINANCE BUDGETING SYSTEM

MOF needs to know the total value of assets across all
ministries for budget planning.

Step 1: MOF developer creates integration code
Step 2: Code calls POST /api/auth/login/ with service account
Step 3: Gets JWT token
Step 4: Calls GET /api/assets/ to list all assets
Step 5: Sums up acquisition_cost for each asset
Step 6: Displays total in MOF's budgeting dashboard

The data flows automatically. No manual data entry.
No phone calls requesting spreadsheets.
Just machine-to-machine communication.
```

---

<a name="ch-20"></a>
## CHAPTER 20: MENTOR MODE

<a name="20-1"></a>
### 20.1 The Mentor Questions

For every concept in this system, always ask yourself these questions:

1. **WHY?** — Why does this exist?
2. **HOW?** — How does it work?
3. **WHO CREATES IT?** — Who or what creates this thing?
4. **WHO RECEIVES IT?** — Who or what receives/consumes this thing?
5. **WHERE IS IT STORED?** — Where does this data live?
6. **WHERE IS IT CONFIGURED?** — Where are the settings for this?
7. **WHO OWNS IT?** — Who is responsible for this?
8. **WHEN IS IT DELETED?** — When does this thing go away?
9. **CAN I SEE IT?** — How do I inspect this?
10. **CAN USERS EDIT IT?** — Can a normal user change this?
11. **CAN ATTACKERS STEAL IT?** — What's the security concern?
12. **WHAT HAPPENS IF IT BREAKS?** — Failure mode?

<a name="20-2"></a>
### 20.2 Applied Mentor Questions — JWT Token

**WHY does JWT exist?**
To prove a user's identity without sending their password on every request.

**HOW does it work?**
Server creates a signed token containing user info. Client sends it on every request. Server verifies the signature.

**WHO CREATES it?**
The server's `LoginAPIView` and `CustomTokenObtainPairSerializer` in `authentication/api_views.py`.

**WHO RECEIVES it?**
The Flutter app (stored in secure storage) or the browser (stored in memory).

**WHERE IS IT STORED?**
Flutter app: secure storage (keychain/keystore). Browser: memory. Not in a database.

**WHERE IS IT CONFIGURED?**
`config/settings.py`, `SIMPLE_JWT` settings.

**WHO OWNS it?**
The user who logged in. But the token expires so "ownership" is temporary.

**WHEN IS IT DELETED?**
After 30 minutes (access token) or 1 day (refresh token). Or when the user logs out.

**CAN I SEE IT?**
Yes. Decode it at jwt.io (paste the token, see the payload). But the signature requires the SECRET_KEY.

**CAN USERS EDIT IT?**
No. If they modify the payload, the signature becomes invalid and the server rejects it.

**CAN ATTACKERS STEAL IT?**
Yes. Through malware, unencrypted WiFi, XSS attacks. Mitigated by short expiry and HTTPS.

**WHAT HAPPENS IF IT BREAKS?**
If the token is rejected, the API returns 401. The Flutter app tries to refresh. If refresh fails, user must log in again.

<a name="20-3"></a>
### 20.3 Applied Mentor Questions — PostgreSQL Schema

**WHY does schema isolation exist?**
To keep each ministry's data completely separate while using one database.

**HOW does it work?**
Each ministry has its own schema (folder) in PostgreSQL. Queries include `SET search_path = moh_schema` to switch.

**WHO CREATES it?**
`tenants/views.py` `ministry_create_view()` when a Super Admin creates a new ministry.

**WHERE IS IT STORED?**
In PostgreSQL's system catalogs. Each schema is a namespace with its own tables.

**WHERE IS IT CONFIGURED?**
In `tenants/models.py` (Ministry model with `auto_create_schema = True`) and `config/settings.py` (TENANT_MODEL, TENANT_DOMAIN_MODEL).

**WHO OWNS it?**
The Ministry Admin for that schema. The schema is created when the Ministry record is saved.

**WHEN IS IT DELETED?**
When the Ministry is deleted. In practice, ministries are deactivated, not deleted.

**CAN I SEE IT?**
Yes. In pgAdmin, connect to `government_assets_db` and expand "Schemas" to see all schemas.

**CAN USERS EDIT IT?**
No. Schema structure is controlled by migrations. Normal users cannot create or modify schemas.

**CAN ATTACKERS STEAL IT?**
The schema itself cannot be stolen. The data within could be accessed through SQL injection (prevented by ORM).

**WHAT HAPPENS IF IT BREAKS?**
If a schema goes missing, users from that ministry cannot access any data. All queries return "relation does not exist."

<a name="20-4"></a>
### 20.4 Applied Mentor Questions — LoginAttempt (Brute Force)

**WHY does this exist?**
To prevent attackers from guessing passwords by trying thousands of combinations.

**HOW does it work?**
Tracks failed attempts per username+IP. After 5 failures, account locks for 15 minutes.

**WHO CREATES it?**
`_record_failed_attempt()` in `authentication/api_views.py` when login fails.

**WHERE IS IT STORED?**
In the `authentication_loginattempt` database table (public schema).

**WHERE IS IT CONFIGURED?**
In `authentication/models.py`: `MAX_ATTEMPTS = 5`, `LOCKOUT_MINUTES = 15`.

**WHO OWNS it?**
The system. Records are created and managed automatically.

**WHEN IS IT DELETED?**
On successful login (`_clear_failed_attempts`). After lockout expires and a new login attempt resets it.

**CAN I SEE IT?**
Yes: `python manage.py shell` → `from authentication.models import LoginAttempt; LoginAttempt.objects.all()`

**CAN USERS EDIT IT?**
No. Users cannot modify their login attempt records. Only the system creates and deletes them.

**CAN ATTACKERS STEAL IT?**
The data is in the database. Attackers could see that a lockout exists (proof of brute-force attempts). Not sensitive.

**WHAT HAPPENS IF IT BREAKS?**
If the table is corrupted, lockout protection is lost. Every login attempt proceeds without lockout checking.

<a name="20-5"></a>
### 20.5 Applied Mentor Questions — AuditLog (Immutability)

**WHY does this exist?**
To provide a legally admissible, tamper-proof record of every action in the system.

**HOW does it work?**
The `save()` method raises PermissionError if the record already exists. `delete()` always raises PermissionError.

**WHO CREATES it?**
Every view and API endpoint that performs an action (CREATE, UPDATE, DELETE, LOGIN, LOGOUT).

**WHERE IS IT STORED?**
In the `organizations_auditlog` table within each ministry's schema.

**WHERE IS IT CONFIGURED?**
In `organizations/models.py`, the `AuditLog` model with overridden `save()` and `delete()`.

**WHO OWNS it?**
The system. No user can own, edit, or delete audit entries. They can only create new ones.

**WHEN IS IT DELETED?**
Never. Audit logs are permanent. A management command could truncate the table (requires database admin).

**CAN I SEE IT?**
Yes: `/audit-logs/` web page or `GET /api/audit-logs/` API. Also directly in the database.

**CAN USERS EDIT IT?**
No. The model raises PermissionError on any attempt to modify or delete.

**CAN ATTACKERS STEAL IT?**
The audit data is in the database. Attackers with database access could read it. Modifying or deleting is prevented by the model (but a DB admin with raw SQL could bypass this).

**WHAT HAPPENS IF IT BREAKS?**
If the `save()` override fails, new actions are not recorded but the system continues working. The breach of audit trail would be logged.

<a name="20-6"></a>
### 20.6 The Final Advice

Before your panel presentation, practice explaining these concepts:

1. **What does this system do?** "It tracks government assets across multiple ministries with role-based access and tamper-proof audit logs."

2. **How does multi-tenancy work?** "Each ministry's data lives in its own PostgreSQL schema. The system switches schemas based on the logged-in user."

3. **How does authentication work?** "Web users log in through Keycloak SSO. Mobile users log in through the API and get JWT tokens."

4. **How does authorization work?** "Five roles control what users can see and do. Web pages use decorators. API endpoints use permission classes."

5. **What security features do you have?** "Nine layers including schema isolation, brute-force protection, immutable audit logs, JWT token security, and Keycloak SSO."

6. **How does the mobile app work?** "It talks to our REST API. Login returns a JWT token. All subsequent requests use the token. There's no Keycloak on mobile."

7. **How would another ministry integrate?** "We create a service account. They call our API with JWT authentication. The verify-token endpoint lets them validate our tokens."

8. **What are the main files?** "manage.py for commands, config/settings.py for configuration, config/urls.py for routing, views.py for logic, models.py for database, api_views.py for API endpoints."

You know this system. Trust that. Breathe. Answer confidently.
