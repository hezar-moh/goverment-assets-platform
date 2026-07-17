# GOVERNMENT ASSET PLATFORM — Concepts & Architecture

> **Purpose:** Understand what this system is, why it exists, how it's built, and how all the pieces fit together.
> **For:** Beginners, panel defense, daily reference.

---

## Table of Contents

- [1. What This System Is](#1-what-this-system-is)
- [2. The Problem It Solves](#2-the-problem-it-solves)
- [3. System Architecture — The Four Components](#3-system-architecture--the-four-components)
- [4. Multi-Tenancy — One Database, Many Ministries](#4-multi-tenancy--one-database-many-ministries)
- [5. The Five User Roles](#5-the-five-user-roles)
- [6. Three Ways to Access the System](#6-three-ways-to-access-the-system)
- [7. IP Addresses, Domains & How They Connect](#7-ip-addresses-domains--how-they-connect)
- [8. What Is a Server / Website / API? (Beginner Foundation)](#8-what-is-a-server--website--api-beginner-foundation)
- [9. Django Request Lifecycle](#9-django-request-lifecycle)
- [10. File-by-File Code Map](#10-file-by-file-code-map)
- [11. config/settings.py Deep Dive](#11-configsettingspy-deep-dive)
- [12. Beginner Misconceptions](#12-beginner-misconceptions)

---

## 1. What This System Is

> A **centralized digital record system** that lets multiple government ministries **track every physical item they own** — from laptops to ambulances to hospital beds — **securely online**, with **each ministry only seeing their own data**, accessible from **both a web browser and a mobile phone**.

**Tech stack:**
- **Django** (Python web framework) — server logic
- **PostgreSQL** — database
- **Keycloak** — Single Sign-On authentication
- **Flutter** — mobile app (separate repository)
- **Railway** — cloud hosting (PaaS)

**Code location:** `D:\government_asset_platform`

---

## 2. The Problem It Solves

Before this system, government assets were tracked on paper notebooks and Excel files. Records were lost, expired equipment stayed in use, and auditors could not verify inventory.

| Problem | Solution |
|---------|----------|
| Lost paper records | Digital database, backed up, searchable |
| Multiple Excel versions | One central system, everyone uses same data |
| Expired equipment (fire extinguishers, medical devices) | Automatic warnings: 90 days, 30 days, expired |
| Audit trail | Every action recorded, nobody can edit or delete |
| Theft | Asset assigned to specific location, tracked |
| Cross-ministry visibility | Each ministry sees only their own data |

**The audit problem:** At year-end, the government auditor inspects. They ask "Show me proof of purchase for these 500 items." If you cannot find the paper, it is treated as **missing government property**. People lose their jobs. Criminal charges can be filed.

**The maintenance problem:** A fire extinguisher needs replacement every 5 years. Without a system, nobody knows when 5 years is up. It stays on the wall, expired. When a fire happens, it does not work. People die.

---

## 3. System Architecture — The Four Components

### 3.1 The Components

| Component | What it does | How to start it |
|-----------|-------------|-----------------|
| **Django** (port 8000) | Main server. Runs Python code. Serves web pages (HTML) and API (JSON). | `python manage.py runserver 0.0.0.0:8000` |
| **PostgreSQL** (port 5432) | Database. Stores ALL data permanently. Runs as a Windows service. | Automatic (Windows starts it) |
| **Keycloak** (port 8180 local, 8080 Railway) | SSO authentication. Handles passwords. Django never stores passwords. | `kc.bat start-dev --http-port=8180` |
| **Flutter** (mobile app) | Phone app. Talks to Django's API via JWT tokens. | `flutter run` in `C:\Users\Hemed\govasset_mobile` |

### 3.2 How They Interact

```
YOUR LAPTOP (local development)
┌──────────────────────────────────────────────────────────┐
│  ┌─────────────────┐   ┌──────────────────┐             │
│  │  Django (8000)   │   │  Keycloak (8180)  │            │
│  │  ┌───────────┐   │   │  Realm: govasset   │           │
│  │  │ Python    │   │   │  Users, Clients    │           │
│  │  │ Code      │   │   └────────┬─────────┘             │
│  │  └───────────┘   │            │                       │
│  └────────┬─────────┘            │                       │
│           │                      │                       │
│           ▼                      ▼                       │
│  ┌──────────────────────────────────────┐                │
│  │  PostgreSQL (5432)                    │               │
│  │  Database: government_assets_db       │               │
│  │  ├─ Schema: public (shared tables)   │               │
│  │  ├─ Schema: moh_schema (MOH data)    │               │
│  │  └─ Schema: mof_schema (MOF data)    │               │
│  └──────────────────────────────────────┘                │
│                                                          │
│  PHONE → Flutter app → http://192.168.x.x:8000/api/     │
│  BROWSER → Web pages → http://localhost:8000/dashboard/  │
└──────────────────────────────────────────────────────────┘
```

### 3.3 Startup Order (Must Follow)

```
1. PostgreSQL — AUTOMATIC (Windows service, always running)
       ↓
2. Django — YOU run: python manage.py runserver 0.0.0.0:8000
       ↓
3. Keycloak — YOU run: kc.bat start-dev --http-port=8180
       ↓
4. Flutter — YOU run: flutter run (separate terminal)
```

**Wrong order problems:**
- Django before PostgreSQL → `could not connect to server`
- Flutter before Django → `connection refused`
- Browser before Keycloak → Keycloak login page is down

### 3.4 The Key Distinctions

| Term | What it means | In our project |
|------|---------------|----------------|
| **Server** | The physical/virtual computer | Your laptop running Django |
| **Backend** | The code that runs ON the server | Our Django Python code |
| **Frontend** | The visual part the user sees | HTML templates OR Flutter app |
| **Database** | Where data is stored permanently | PostgreSQL |

---

## 4. Multi-Tenancy — One Database, Many Ministries

### 4.1 What It Means

**Single platform, multiple ministries, complete data isolation.**

Each ministry gets its own **PostgreSQL schema** — a separate set of tables within the same database. django-tenants routes every request to the correct schema.

```
One Database "government_assets_db"
├── Schema: public
│   ├── authentication_customuser     (users — shared)
│   ├── tenants_ministry              (ministry definitions)
│   └── tenants_domain                (domain → schema mapping)
│
├── Schema: moh_schema
│   ├── assets_asset                  (MOH's assets only)
│   ├── organizations_auditlog        (MOH's audit only)
│   └── organizations_orgunit         (MOH's org structure)
│
├── Schema: mof_schema
│   ├── assets_asset                  (MOF's assets only)
│   ├── organizations_auditlog        (MOF's audit only)
│   └── organizations_orgunit         (MOF's org structure)
│
└── Schema: moe_schema (future — Education)
```

### 4.2 Shared vs Tenant Apps

| Type | Apps | Tables live in |
|------|------|---------------|
| **SHARED_APPS** | `authentication`, `tenants` | `public` schema |
| **TENANT_APPS** | `assets`, `organizations` | Each ministry's schema |

### 4.3 How Domain-to-Ministry Routing Works

```
Browser visits: http://moh.localhost:8000/dashboard/

Step 1: Browser resolves moh.localhost → 127.0.0.1 (localhost)
        (.localhost always points to your computer — no DNS needed)

Step 2: Django receives the request

Step 3: TenantMainMiddleware reads Host header: "moh.localhost:8000"
        Looks up in Domain table:
        SELECT * FROM tenants_domain WHERE domain = 'moh.localhost'
        → Finds: tenant_id = 1 (Ministry of Health)

Step 4: Sets database search_path: SET search_path = moh_schema;
        Now ALL queries use moh_schema tables

Step 5: View runs, queries the database — all go to moh_schema
```

**For IP access (mobile app via hotspot):**
- Host header is `192.168.100.18:8000` — not found in Domain table
- Falls back to `public` schema via `SHOW_PUBLIC_IF_NO_TENANT_FOUND = True`
- After user logs in, `request.user.ministry_schema` tells the view which schema to use
- Views use `with schema_context(user.ministry_schema):` to query the correct schema

### 4.4 Creating a New Ministry

Super Admin visits `/ministries/create/`:
1. Creates `Ministry` record (`auto_create_schema = True` — automatically creates PostgreSQL schema)
2. Runs migrations for tenant apps in the new schema
3. Creates `Domain` record (maps domain → schema)
4. Creates root `OrgUnit` for the ministry
5. **Ministry is live in under a minute. Zero downtime for other ministries.**

### 4.5 Why Not Separate Systems Per Ministry?

| Separate systems | One platform (ours) |
|-----------------|---------------------|
| 20 servers × 20 databases | 1 server, 1 database |
| 20 separate backups | 1 backup |
| 20 different login pages | 1 SSO login |
| No cross-ministry view | Super Admin sees everything |
| 20× the cost | 1× the cost |

---

## 5. The Five User Roles

| Role | Level | What they can do |
|------|-------|-----------------|
| **SUPER_ADMIN** | Central government | Sees everything across ALL ministries. Manages ministries. Creates/receives ministry-level users. No personal assets. |
| **MINISTRY_ADMIN** | Ministry-wide | Full access within their ministry. Creates users, manages all assets, sees audit logs. |
| **AGENCY_MANAGER** | Agency level | Manages an agency under a ministry (e.g., all hospitals under MOH). |
| **FACILITY_CLERK** | Facility level | Manages one facility (e.g., one hospital). Can add/edit assets at their location. |
| **AUDITOR** | Read-only | Can see everything but cannot change anything. For government inspections. |

**Real government example:**
```
Dr. Amina Hassan is ICT Director at Ministry of Health.
  Role: MINISTRY_ADMIN
  Can: See all 9,472 MOH assets, create users, edit records, view audit logs
  Cannot: See Ministry of Finance data, see Ministry of Education data

Mr. Juma Omary is Super Admin at President's Office.
  Can: Add ministries, see statistics across ALL ministries
  But: Has NO personal assets
```

### 5.1 Permission Matrix

| Action | SUPER_ADMIN | MINISTRY_ADMIN | AGENCY_MANAGER | FACILITY_CLERK | AUDITOR |
|--------|:-----------:|:--------------:|:--------------:|:--------------:|:-------:|
| View assets | ✓ | ✓ | ✓ | ✓ | ✓ |
| Create assets | ✓ | ✓ | ✓ | ✓ | ✗ |
| Edit assets | ✓ | ✓ | ✓ | ✓ | ✗ |
| Delete assets | ✓ | ✓ | ✗ | ✗ | ✗ |
| View audit logs | ✓ | ✓ | ✓ | ✗ | ✓ |
| Manage users | ✓ | ✓ | ✗ | ✗ | ✗ |
| Manage ministries | ✓ | ✗ | ✗ | ✗ | ✗ |

---

## 6. Three Ways to Access the System

| Method | How | When to use |
|--------|-----|-------------|
| **Web Browser** | Visit `http://localhost:8000/` or the Railway URL | Full management interface. HTML tables, forms, buttons. |
| **Flutter Mobile App** | Phone app via API at `http://192.168.x.x:8000/api/` | Mobile-optimized. Asset list, details, quick actions. |
| **API (Machine-to-Machine)** | External systems call `POST /api/auth/login/` etc. | Other government systems integrating with this platform. |

**Web vs API — Same data, different format:**
```
WEB BROWSER sees:           API returns:
┌────────┬────────┐         {"count": 2, "results": [
│ Number │ Name   │           {"asset_number": "MOH-01", "name": "Laptop"},
├────────┼────────┤           {"asset_number": "MOH-02", "name": "Truck"}
│ MOH-01 │ Laptop │         ]}
│ MOH-02 │ Truck  │
└────────┴────────┘
HTML (with layout)          JSON (pure data for programs)
```

---

## 7. IP Addresses, Domains & How They Connect

### 7.1 The Four Addresses of Your Laptop

| Address | What it means | Who can use it |
|---------|-------------|----------------|
| `localhost` (or `127.0.0.1`) | "This computer only" | Programs on YOUR laptop only |
| `0.0.0.0` | "ALL network interfaces" (a command, not a URL) | Tells Django to listen everywhere |
| `192.168.100.18` | Your laptop's real address on hotspot/network | Phone on hotspot, other devices |

**Key rule:**
- `python manage.py runserver` → listens on localhost only (phone CANNOT reach it)
- `python manage.py runserver 0.0.0.0:8000` → listens everywhere (phone CAN reach it)

**`0.0.0.0` is NOT a URL you type.** It is a command meaning "listen everywhere." You visit `http://192.168.100.18:8000/` instead.

### 7.2 Domain Routing (Development)

```
moh.localhost:8000  →  Ministry of Health   (moh_schema)
mof.localhost:8000  →  Ministry of Finance  (mof_schema)
localhost:8000       →  Public schema (Super Admin)
```

`.localhost` always resolves to `127.0.0.1` on your own computer — **no DNS or internet needed.**

### 7.3 How the Phone Finds the Laptop

```
Phone on hotspot → http://192.168.100.18:8000/api/assets/
                         ↓
              Hotspot delivers to laptop
                         ↓
              Django (listening on 0.0.0.0:8000)
                         ↓
              Responds with JSON data
```

**The phone does NOT need internet.** The hotspot creates a private WiFi network between phone and laptop.

**If IP changes:** Run `ipconfig`, find new IPv4 address, update:
1. Flutter config: `C:\Users\Hemed\govasset_mobile\lib\config\api_config.dart`
2. `ALLOWED_HOSTS` in Railway Django Variables tab

### 7.4 What Happens When You Visit a URL

```
YOU TYPE: http://localhost:8000/dashboard/

Step 1: Browser parses → protocol(http) + address(localhost) + port(:8000) + path(/dashboard/)
Step 2: Browser resolves localhost → 127.0.0.1 (your computer)
Step 3: Browser sends: GET /dashboard/ HTTP/1.1  Host: localhost:8000
Step 4: Django checks URL patterns (config/urls.py) → finds dashboard_view
Step 5: dashboard_view runs → checks your role → queries database → renders template
Step 6: Django returns HTML page → browser renders it visually
```

---

## 8. What Is a Server / Website / API? (Beginner Foundation)

### 8.1 What Is a Server?

A **server** is just a computer that sits in a room and waits for requests. Your laptop is a computer you actively use. A server is a computer that does what other computers tell it to do.

**Analogy — A restaurant:**
- You = the **client** (customer)
- The waiter = the **server** (Django)
- The kitchen = the **database** (PostgreSQL)
- The menu = the **website** (HTML pages)

You tell the waiter what you want (request). The waiter goes to the kitchen (database), gets your food (data), and brings it back (response).

### 8.2 What Is a Website?

A **website** is a collection of HTML pages that are GENERATED on the fly by Django. The templates are stored on disk, but the DATA that fills them comes from the database.

Template is like a form letter: `"Hello {{ name }}, you have {{ count }} assets."`
Data fills in the blanks: `"Hello Amina, you have 9 assets."`

### 8.3 What Is an API?

**API = Application Programming Interface.** A way for one piece of software to talk to another piece of software.

- **Websites** return HTML (for humans to read in a browser)
- **APIs** return JSON (for programs to read)

The Flutter app cannot load HTML — it is not a browser. It needs JSON data to display using its own visual components.

### 8.4 HTTP Methods

| Method | Meaning | Example |
|--------|---------|---------|
| **GET** | "Give me data" (read) | `GET /api/assets/` — list assets |
| **POST** | "Create something new" | `POST /api/auth/login/` — log in |
| **PUT** | "Replace entirely" (update) | `PUT /api/assets/42/` — update asset |
| **DELETE** | "Delete something" | `DELETE /api/assets/42/` — delete asset |

### 8.5 What Would Happen Without Each Piece

| Missing piece | What happens |
|---------------|--------------|
| No `urls.py` | Django receives request but doesn't know what code to run → 404 |
| No template | View runs, query runs, but Django can't build HTML → 500 error |
| No CSS | HTML works but looks plain — black text on white |
| No database | View can't load data → 500 error |
| No model | Database table doesn't exist → query fails → 500 error |

---

## 9. Django Request Lifecycle

A complete request from start to finish:

```
Flutter App (or Browser)
        │
        ▼  HTTP Request (e.g., GET /api/assets/)
NETWORK │
        │
        ▼
DJANGO  │
        │
  1. WSGI/Gunicorn receives the request
        │
  2. Middleware Pipeline (in order):
     a. MaintenanceModeMiddleware — is system under maintenance?
     b. TenantMainMiddleware — determine schema from domain
     c. SecurityMiddleware — HTTPS redirect, security headers
     d. SessionMiddleware — load session from cookie
     e. AuthenticationMiddleware — attach user to request
     f. SchemaMiddleware — set schema from user profile
     g. CSRFMiddleware — check CSRF token (web forms only)
     h. AuthMiddleware — check authentication
     i. MessageMiddleware — flash messages
     j. XFrameOptionsMiddleware — clickjacking protection
        │
  3. URL Router (config/urls.py) → finds matching view
        │
  4. View Function runs:
     a. Permission check (decorators for web, permission classes for API)
     b. Business logic (query database, process data)
     c. For web: render HTML template
     d. For API: serialize data to JSON
        │
  5. HTTP Response sent back to client
        │
        ▼
CLIENT receives response, displays data
```

**Total time:** ~30ms for a simple API call, ~50ms for a rendered page.

---

## 10. File-by-File Code Map

### 10.1 Authentication App

| File | Purpose |
|------|---------|
| `authentication/models.py` | `CustomUser` (with `keycloak_id`, `role`, `ministry_schema`), `PendingAccess`, `LoginAttempt` |
| `authentication/views.py` | Web views for login, logout, profile |
| `authentication/dashboard_views.py` | Dashboard with expiry warnings (90/30/expired) |
| `authentication/user_views.py` | User management: create, edit, activate/deactivate, reset password — syncs with Keycloak |
| `authentication/pending_access_views.py` | Admin approves/rejects new users who logged in via SSO but have no Django profile |
| `authentication/api_views.py` | API: login, refresh, verify-token, me, logout |
| `authentication/api_urls.py` | URL routing for all API endpoints |
| `authentication/api_serializers.py` | Converts DB objects ↔ JSON for API |
| `authentication/api_permissions.py` | 7 permission classes: IsSuperAdmin, IsMinistryAdmin, CanManageAssets, etc. |
| `authentication/auth_backend.py` | Custom auth — validates passwords against Keycloak REST API |
| `authentication/oidc_backend.py` | OIDC bridge — syncs Keycloak users ↔ Django users on every SSO login |
| `authentication/keycloak_admin.py` | Keycloak Admin REST API client — create/update/delete users in Keycloak |
| `authentication/middleware.py` | `SchemaMiddleware` — sets PostgreSQL schema from user profile |
| `authentication/decorators.py` | `login_required_custom`, `role_required('MINISTRY_ADMIN')`, `ministry_isolation_check` |
| `authentication/pagination.py` | Paginates API lists (20 items/page) |
| `authentication/management/commands/setup_demo_data.py` | Seeds demo users, assets, audit logs |
| `authentication/management/commands/sync_keycloak_attributes.py` | Pushes `role`/`ministry_schema` attributes to existing Keycloak users |

### 10.2 Assets App

| File | Purpose |
|------|---------|
| `assets/models.py` | `Asset` (asset_number, name, category, status, condition, expiry, etc.), `AssetCategory` |
| `assets/views.py` | Web: list, create, edit, delete assets |
| `assets/api_views.py` | API: list (with filters), create, detail, update, delete — with auto-numbering and field-level audit |

### 10.3 Organizations App

| File | Purpose |
|------|---------|
| `organizations/models.py` | `OrgUnit` (3-level hierarchy), `MasterData` (reference lists), `AuditLog` (tamper-proof) |
| `organizations/views.py` | Web: org unit tree, audit log viewer |
| `organizations/api_views.py` | API: org units, audit logs, dashboard stats |
| `organizations/master_data_views.py` | Web: manage reference data + asset categories |

### 10.4 Tenants App

| File | Purpose |
|------|---------|
| `tenants/models.py` | `Ministry` (with `auto_create_schema = True`), `Domain` (domain → schema mapping) |
| `tenants/views.py` | Web: create, list, detail ministries |

### 10.5 Config & Templates

| File | Purpose |
|------|---------|
| `config/settings.py` | EVERY setting — database, apps, middleware, JWT, OIDC, logging, security |
| `config/urls.py` | Master URL routing — maps every URL to its view |
| `templates/shared/base.html` | Main layout — header, sidebar, footer — ALL pages extend this |
| `templates/shared/pagination.html` | Page number buttons |
| `templates/dashboard/dashboard.html` | Dashboard page |
| `templates/authentication/*.html` | Login, user management pages |
| `templates/assets/*.html` | Asset list, form, detail pages |
| `templates/organizations/*.html` | Org unit, master data, audit log, asset category pages |
| `templates/tenants/*.html` | Ministry management pages |
| `static/css/style.css` | ALL CSS — including responsive rules |

### 10.6 File Dependency Diagram

```
manage.py → config/settings.py
                │
                ├── config/urls.py → maps URLs to views
                │       ├── authentication/*_views.py
                │       ├── authentication/api_urls.py → api_views.py
                │       ├── assets/views.py & api_views.py
                │       ├── organizations/views.py & api_views.py & master_data_views.py
                │       └── tenants/views.py
                │
                ├── authentication/middleware.py (SchemaMiddleware)
                ├── authentication/oidc_backend.py (Keycloak bridge)
                ├── authentication/keycloak_admin.py (Keycloak API)
                ├── authentication/models.py (CustomUser, PendingAccess, LoginAttempt)
                ├── assets/models.py (Asset, AssetCategory)
                ├── organizations/models.py (OrgUnit, MasterData, AuditLog)
                └── tenants/models.py (Ministry, Domain)
```

---

## 11. config/settings.py Deep Dive

**File:** `config/settings.py` (619 lines)
**Why it exists:** Every setting for the entire project lives here. Without it, Django wouldn't know what database to use, what apps are installed, or how to handle authentication.

### 11.1 SHARED_APPS vs TENANT_APPS (Lines 28–70)

```python
SHARED_APPS = [
    'django_tenants',    # Multi-tenancy system itself
    'tenants',           # Ministry model (shared across all)
    'authentication',    # CustomUser — ONE table for ALL ministries
    'django.contrib.admin',
    'django.contrib.auth',
    # ... other Django built-ins
]

TENANT_APPS = [
    'organizations',     # Org unit, audit log — SEPARATE per ministry
    'assets',            # Assets — SEPARATE per ministry
]

TENANT_MODEL = "tenants.Ministry"
TENANT_DOMAIN_MODEL = "tenants.Domain"
SHOW_PUBLIC_IF_NO_TENANT_FOUND = True  # Allows IP-based access
```

### 11.2 Middleware Order (Lines 100–130) — Critical!

```python
MIDDLEWARE = [
    'django_tenants.middleware.maintenance.MaintenanceModeMiddleware',
    'django_tenants.middleware.TenantMainMiddleware',  # MUST be first!
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'authentication.middleware.SchemaMiddleware',       # Sets schema from user
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]
```

**Order matters:**
1. TenantMainMiddleware runs FIRST — determines schema from domain BEFORE anything else
2. SchemaMiddleware runs AFTER AuthenticationMiddleware — sets schema from user profile after login

### 11.3 Database Configuration (Lines 135–145)

```python
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',  # Adds SET search_path!
        'NAME': 'gov_asset_platform',
        'USER': 'postgres',
        'PASSWORD': '...',
        'HOST': 'localhost',
        'PORT': '5432',
        'OPTIONS': {'options': '-c search_path=public'}
    }
}
```

The special `ENGINE` is what makes multi-tenancy work. Django-tenants adds `SET search_path = <schema>` before every query.

### 11.4 Authentication (Lines 180–187)

```python
AUTH_USER_MODEL = 'authentication.CustomUser'  # Custom user, not Django's default

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',             # For superuser login
    'authentication.oidc_backend.CustomOIDCBackend',         # Keycloak SSO
    'authentication.auth_backend.APIAuthBackend',            # Mobile app login
]
```

### 11.5 JWT Settings (Lines 217–235)

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),   # Short-lived
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),      # Longer-lived
    'ROTATE_REFRESH_TOKENS': True,                    # New refresh token each use
    'BLACKLIST_AFTER_ROTATION': True,                 # Old one stops working
    'AUTH_HEADER_TYPES': ('Bearer',),
    'TOKEN_OBTAIN_SERIALIZER': 'authentication.api_serializers.CustomTokenObtainPairSerializer',
}
```

### 11.6 DRF Settings (Lines 240–260)

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
    'DEFAULT_THROTTLE_CLASSES': ['rest_framework.throttling.UserRateThrottle'],
    'DEFAULT_THROTTLE_RATES': {'user': '100/hour'},
}
```

### 11.7 Logging (Lines 461–510)

```python
LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {message}', 'style': '{'},
    },
    'handlers': {
        'django_file': {'class': 'logging.FileHandler', 'filename': 'logs/django.log'},
        'security_file': {'class': 'logging.FileHandler', 'filename': 'logs/security.log'},
    },
    'loggers': {
        'django': {'handlers': ['django_file'], 'level': 'INFO'},
        'security': {'handlers': ['security_file'], 'level': 'INFO'},
    },
}
```

- `logs/django.log` — General Django activity (2920 lines so far — old 404s and fixed 500s)
- `logs/security.log` — Login/logout audit trail (677 lines — every authentication event)

### 11.8 Security Headers (Lines 430–460)

```python
SECURE_BROWSER_XSS_FILTER = True       # Enable browser XSS protection
SECURE_CONTENT_TYPE_NOSNIFF = True     # Prevent MIME sniffing
X_FRAME_OPTIONS = 'DENY'              # Prevent clickjacking
SESSION_COOKIE_HTTPONLY = True         # JS can't read session cookie
CSRF_COOKIE_HTTPONLY = True           # JS can't read CSRF cookie
SESSION_COOKIE_SAMESITE = 'Lax'       # Prevent CSRF from external sites
```

### 11.9 Quick Reference — Common Changes

| Task | Setting to change | File:Line |
|------|------------------|-----------|
| Add a new app | Add to SHARED_APPS or TENANT_APPS | `settings.py:28-70` |
| Change JWT expiry | `SIMPLE_JWT['ACCESS_TOKEN_LIFETIME']` | `settings.py:217` |
| Change rate limit | `REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']` | `settings.py:258` |
| Add a middleware | Insert in `MIDDLEWARE` list | `settings.py:100` |
| Point to production Keycloak | Change OIDC endpoints | `settings.py:527-598` |
| Disable IP-based access | Set `SHOW_PUBLIC_IF_NO_TENANT_FOUND = False` | `settings.py` |

---

## 12. Beginner Misconceptions

### 12.1 About the System

| Misconception | Truth |
|--------------|-------|
| "Each ministry needs their own server" | One server serves all ministries. Database schemas separate their data. |
| "If I can log in, I can see everything" | Your role determines what you see. A Facility Clerk sees only their facility. |
| "The mobile app is a separate system" | Same server, same database, same auth. Just a different way to access (API vs HTML). |
| "This is just an inventory app" | It is an asset LIFECYCLE system — planned → acquired → active → maintenance → disposed. |

### 12.2 About Servers and Databases

| Misconception | Truth |
|--------------|-------|
| "The internet is required for everything" | This system runs entirely on your local network (hotspot). No internet needed. |
| "The database is inside Django" | PostgreSQL is a completely separate program. Django connects to it. |
| "Python runs all the time" | Python/Django only runs when you type `runserver`. Close terminal → stops. |

### 12.3 About IP Addresses

| Misconception | Truth |
|--------------|-------|
| "0.0.0.0 is an address I can visit" | It's a command meaning "listen everywhere." You visit `http://192.168.x.x:8000/`. |
| "localhost and 127.0.0.1 are different" | They are the SAME thing. localhost = name, 127.0.0.1 = IP. |
| "The IP address never changes" | Your hotspot IP changes every time you connect to a different network. |
| "I need to buy a domain for development" | For development, use `.localhost` domains — they work immediately. |

### 12.4 About APIs and Websites

| Misconception | Truth |
|--------------|-------|
| "The browser loads a file directly from the laptop" | Django receives the request, runs code, queries DB, generates HTML dynamically. |
| "The URL is the file path on the server" | URLs are mapped to Python code. `/assets/` doesn't mean a folder called `assets`. |
| "HTML is what the server stores" | HTML is GENERATED on the fly. Templates store structure, data comes from DB. |
| "JWT is the login system" | JWT is the OUTPUT of a successful login. Login is the process of verifying credentials. |
| "A JWT is like a password" | A JWT expires in 30 minutes. A password lasts forever (until changed). |

---

## 13. JWT Token Structure

```
┌──────────────────────────────────────────────────────────────┐
│                        JWT TOKEN                               │
├──────────────────────────────────────────────────────────────┤
│                                                                │
│  HEADER (Base64 decoded)                                      │
│  ┌────────────────────────────────────────────────────┐      │
│  │ {                                                   │      │
│  │   "alg": "HS256",       ← Algorithm used to sign  │      │
│  │   "typ": "JWT"          ← Type of token           │      │
│  │ }                                                   │      │
│  └────────────────────────────────────────────────────┘      │
│                                                                │
│  PAYLOAD (Base64 decoded)                                     │
│  ┌────────────────────────────────────────────────────┐      │
│  │ {                                                   │      │
│  │   "token_type": "access",  ← Is this access/refresh│      │
│  │   "exp": 1700000000,       ← Expiration timestamp  │      │
│  │   "iat": 1699998200,       ← Issued at timestamp   │      │
│  │   "jti": "abc123",         ← Unique token ID       │      │
│  │   "user_id": 1,            ← Which user            │      │
│  │   "role": "MINISTRY_ADMIN",  ← User's role         │      │
│  │   "ministry_schema": "moh_schema" ← User's schema  │      │
│  │ }                                                   │      │
│  └────────────────────────────────────────────────────┘      │
│                                                                │
│  SIGNATURE (created by the server):                           │
│  HMAC-SHA256(                                                  │
│    base64(header) + "." + base64(payload),                     │
│    SECRET_KEY                                                  │
│  )                                                             │
│                                                                │
└──────────────────────────────────────────────────────────────┘
```

---

## 14. Login Flow Diagrams

### 14.1 Web Login via Keycloak (SSO)

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

### 14.2 Mobile API Login (JWT)

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

---

## 15. Real Government Scenarios

### 15.1 Scenario: Expired Asset Discovery

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

### 15.2 Scenario: Onboarding a New Ministry

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

### 15.3 Scenario: Auditor Reviews Asset Records

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

### 15.4 Scenario: Mobile Field Clerk Updates Asset

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

### 15.5 Scenario: Finance Ministry Integrates

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
