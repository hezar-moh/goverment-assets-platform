# GOVERNMENT ASSET MANAGEMENT PLATFORM — COMPLETE EXPLANATION

> **Read this file from top to bottom. It explains everything about the project in plain language, assuming you have never written code before.**

---

## TABLE OF CONTENTS

1. [What is this project?](#1-what-is-this-project)
2. [Technologies used — explained simply](#2-technologies-used)
3. [Project folder structure](#3-project-folder-structure)
4. [Each file explained](#4-each-file-explained)
5. [Security features](#5-security-features)
6. [How a request travels through the system](#6-how-a-request-travels)
7. [The key commands](#7-the-key-commands)
8. [Common panel questions and answers](#8-common-panel-questions)

---

## 1. WHAT IS THIS PROJECT?

**In one sentence:** A web + mobile system for Tanzanian government ministries to track their physical assets (laptops, vehicles, medical equipment, furniture, etc.) from purchase to disposal.

**Real-world example:** Imagine the Ministry of Health has 10,000 laptops, 500 ambulances, and 2,000 hospital beds. They need to know:
- Where is each asset right now?
- Who is using it?
- When does its warranty expire?
- When should it be replaced?
- How much did it cost?

Before this system: paper records and Excel sheets (lost data, no tracking).
After this system: one online platform where every asset is tracked.

**Who uses it?**
- **Super Admin** — Runs the entire platform, adds new ministries
- **Ministry Admin** — Manages one ministry's assets and users
- **Agency Manager** — Manages assets in an agency (e.g., all hospitals under MOH)
- **Facility Clerk** — Manages assets in one facility (e.g., one specific hospital)
- **Auditor** — Can view everything (read-only) for inspection

---

## 2. TECHNOLOGIES USED

Every technology is explained simply — what problem it solves and why we chose it.

### Python / Django (version 5.x)
- **What it is:** The main programming language and framework that runs the entire website.
- **Why:** Django is the most popular web framework for government systems worldwide. It comes with built-in security features (protects against common attacks), an admin panel, and a user system.
- **What our Django does:** Handles browser pages AND mobile app requests.

### PostgreSQL (database)
- **What it is:** The storage system where all data lives — user accounts, assets, audit logs.
- **Why:** PostgreSQL is free, reliable, and has a special feature called "schemas" that lets us separate each ministry's data. MySQL (another database) does NOT have this feature.
- **Where it runs:** As a Windows service in the background. It starts automatically when you turn on the laptop.

### django-tenants (multi-tenancy)
- **What it is:** A special Django add-on that creates a separate section (schema) in the database for each ministry.
- **Why:** When Ministry of Health logs in, they see ONLY their assets. When Ministry of Finance logs in, they see ONLY their assets. Both use the same website and same database, but their data is completely walled off.
- **How it works:** When you create "Ministry of Health" in the system, Django automatically creates a new schema called `moh_schema`. All MOH data goes there.

### Django REST Framework (DRF) — the API
- **What it is:** A system that lets the mobile phone app talk to the website server.
- **Why:** The web pages (HTML) and the mobile app (Flutter) need the same data. The API is a middle-man that both can use.
- **Think of it like a waiter:** The web browser and the mobile app give orders to the waiter (API), and the waiter brings back the food (data) from the kitchen (database).

### Keycloak — SSO (Single Sign-On)
- **What it is:** A separate program that handles passwords. It runs on port 8180.
- **Why:** Instead of typing passwords into our website, users type into Keycloak's secure page. This is more secure because we never see or store the password.
- **SSO (Single Sign-On):** One password works across multiple government systems, not just ours. Like using Google Login for many different websites.
- **Note:** The mobile app does NOT use Keycloak (would be awkward to open a browser page). Mobile sends username/password directly to Django, which also works.

### JWT (JSON Web Token) — the digital pass
- **What it is:** A temporary digital ID card.
- **How it works:** When you log in, the system gives you a token (like a hotel key card). For the next 30 minutes, you can show that token to do things. After 30 minutes, it expires and you need a new one.
- **Why:** The token is signed with a secret code, so nobody can fake it.

### Flutter (mobile app)
- **What it is:** A Google framework for building phone apps.
- **Where:** `C:\Users\Hemed\govasset_mobile` (on your laptop).
- **Why:** One codebase works on both Android and iPhone.

### Swagger / OpenAPI — the documentation
- **What it is:** A visual page showing every available API endpoint.
- **Where:** `http://localhost:8000/api/docs/` when the server is running.
- **Why:** Other government groups can see exactly how to connect to our system.

---

## 3. PROJECT FOLDER STRUCTURE

```
D:\government_asset_platform\
│
├── .env                          ← SECRET config (passwords, keys)
├── .gitignore                    ← Files NOT to save to Git
├── manage.py                     ← Django's command centre
├── requirements.txt              ← List of all Python packages needed
├── config/                       ← Main Django configuration
│   ├── __init__.py               ← Marks this as a Python package
│   ├── settings.py               ← ALL settings in one place (619 lines)
│   ├── urls.py                   ← Every web page URL defined here
│   ├── wsgi.py                   ← For deploying to a real server
│   └── asgi.py                   ← For real-time features (future)
│
├── authentication/               ← User accounts, login, API auth
│   ├── models.py                 ← Database structure for users
│   ├── views.py                  ← Login/logout web pages
│   ├── api_views.py              ← Login/logout API (for mobile app)
│   ├── api_urls.py               ← API web addresses
│   ├── api_serializers.py        ← API data formatting
│   ├── api_permissions.py        ← API access rules
│   ├── dashboard_views.py        ← The dashboard/home page
│   ├── user_views.py             ← Admin pages for managing users
│   ├── pending_access_views.py   ← Pages for approving blocked users
│   ├── decorators.py             ← Access control rules (role checking)
│   ├── middleware.py             ← Runs on EVERY request
│   ├── oidc_backend.py           ← Keycloak integration logic
│   ├── keycloak_admin.py         ← Talks to Keycloak for user management
│   ├── pagination.py             ← Splits long lists into pages
│   ├── admin.py                  ← Django admin panel config
│   ├── tests.py                  ← Automated tests
│   ├── management/commands/
│   │   ├── setup_demo_data.py    ← Creates demo data for presentation
│   │   └── __init__.py
│   └── migrations/               ← Database change history
│
├── assets/                       ← Asset tracking
│   ├── models.py                 ← Database structure for assets
│   ├── views.py                  ← Asset web pages (list, create, edit, delete)
│   ├── api_views.py              ← Asset API (for mobile app)
│   ├── admin.py                  ← Django admin panel config
│   ├── tests.py                  ← Automated tests
│   └── migrations/
│
├── organizations/                ← Organisation hierarchy + audit
│   ├── models.py                 ← Org units, master data, audit log
│   ├── views.py                  ← Org unit + audit web pages
│   ├── api_views.py              ← Org unit + dashboard API
│   ├── master_data_views.py      ← Reference data pages (categories, etc.)
│   ├── admin.py                  ← Django admin panel config
│   ├── tests.py                  ← Automated tests
│   └── migrations/
│
├── tenants/                      ← Ministry management
│   ├── models.py                 ← Ministry and Domain models
│   ├── views.py                  ← Ministry management web pages
│   ├── admin.py                  ← Django admin panel config
│   ├── tests.py                  ← Automated tests
│   └── migrations/
│
├── templates/                    ← HTML page templates
│   ├── shared/
│   │   ├── base.html             ← The main layout (all pages extend this)
│   │   └── pagination.html       ← Page number buttons
│   ├── dashboard/
│   │   └── dashboard.html        ← The home page
│   ├── authentication/
│   │   ├── login.html
│   │   ├── user_form.html
│   │   ├── user_list.html
│   │   ├── user_edit.html
│   │   ├── user_reset_password.html
│   │   ├── pending_access_list.html
│   │   └── pending_access_review.html
│   ├── assets/
│   │   ├── asset_list.html
│   │   ├── asset_form.html       ← Create + Edit shared form
│   │   ├── asset_detail.html
│   │   └── asset_delete.html
│   ├── organizations/
│   │   ├── org_unit_list.html
│   │   ├── org_unit_form.html
│   │   ├── org_unit_edit.html
│   │   ├── master_data_list.html
│   │   ├── master_data_form.html
│   │   ├── master_data_edit.html
│   │   ├── asset_category_list.html
│   │   ├── asset_category_form.html
│   │   ├── asset_category_edit.html
│   │   └── audit_log.html
│   └── tenants/
│       ├── ministry_list.html
│       ├── ministry_form.html
│       └── ministry_detail.html
│
├── static/                       ← Files served to browser as-is
│   ├── css/
│   │   └── style.css             ← The site's visual design
│   └── js/                       ← (empty, ready for JavaScript)
│
├── logs/                         ← Written log files
│   ├── .gitkeep
│   ├── django.log                ← General Django activity
│   └── security.log              ← Login attempts, blocked access
│
└── venv/                         ← Virtual environment (all packages)
```

---

## 4. EACH FILE EXPLAINED

This section goes through every important file and explains what it does, what the key code does, and why it matters.

---

### 4.1 `.env` — The Secret Vault

**Purpose:** Stores all passwords, secret keys, and configuration that should NEVER be shared. This file is listed in `.gitignore` so it won't be uploaded to GitHub.

| Setting | Example Value | What It Does |
|---------|--------------|--------------|
| `SECRET_KEY` | `django-insecure-...` | A secret string Django uses to sign cookies, tokens, sessions. If someone steals this, they can fake login sessions. |
| `DEBUG=True` | `True` | Shows error details during development. Must be `False` in production. |
| `DB_NAME` | `government_assets_db` | The PostgreSQL database name |
| `DB_USER` | `postgres` | Database username |
| `DB_PASSWORD` | `123` | Database password |
| `KEYCLOAK_SERVER_URL` | `http://localhost:8180` | Where Keycloak is running |
| `KEYCLOAK_CLIENT_SECRET` | `i9bDUIzr...` | A password that lets Django talk to Keycloak |

**Why it matters:** If this file leaks, anyone can access your database and Keycloak.

---

### 4.2 `manage.py` — The Control Panel

**Purpose:** This is the ONLY file you run directly. Every command goes through this file.

**Example commands:**
```
python manage.py runserver                 → Start the website
python manage.py makemigrations             → Prepare database changes
python manage.py migrate                    → Apply database changes
python manage.py createsuperuser            → Create admin account
python manage.py setup_demo_data            → Fill database with demo data
python manage.py shell                      → Open a Python command line
```

**How it works (the code):**
```python
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
```
This line tells Django: "Look in the `config` folder, in the file called `settings.py`, for all your configuration." This is how Django knows what database to use, what apps are installed, etc.

---

### 4.3 `config/settings.py` — The Central Brain (619 lines)

**Purpose:** Every single setting for the entire project lives here. This is the most important file.

**Breaking it down into simple parts:**

**A) Multi-Tenancy Setup (lines 28-70)**
```python
SHARED_APPS = [
    'django_tenants',       # The multi-tenancy system itself
    'tenants',              # Ministry model (Ministry names, schema names)
    'authentication',       # User accounts — same table for ALL ministries
    ...
]

TENANT_APPS = [
    'organizations',        # Org hierarchy + audit log — SEPARATE per ministry
    'assets',               # Asset records — SEPARATE per ministry
]
```
**The Magic:** All user accounts live in ONE table (shared). But each ministry gets its OWN copy of the assets and organizations tables inside its own database schema. When a user from MOH logs in, Django automatically switches to the MOH schema.

**B) Database Configuration (lines 135-143)**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': config('DB_NAME'),
        'USER': config('DB_USER'),
        'PASSWORD': config('DB_PASSWORD'),
        'HOST': config('DB_HOST'),
        'PORT': config('DB_PORT'),
    }
}
```
We use a special database engine (`django_tenants.postgresql_backend`) instead of the standard one. This engine adds `SET search_path = moh_schema` before every query so PostgreSQL knows which schema to look in.

**C) JWT Token Settings (lines 217-235)**
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    ...
}
```
- **Access token:** Works for 30 minutes. Like a hotel key card.
- **Refresh token:** Works for 1 day. Like a receipt you can use to get a new key card.
- **ROTATE_REFRESH_TOKENS = True:** Every time you use a refresh token, the old one stops working. This prevents stolen tokens from being reused.
- **BLACKLIST_AFTER_ROTATION = True:** Dead tokens go on a "no entry" list.

**D) OIDC / Keycloak Settings (lines 527-598)**
```python
OIDC_RP_CLIENT_ID = config('KEYCLOAK_CLIENT_ID')
OIDC_RP_CLIENT_SECRET = config('KEYCLOAK_CLIENT_SECRET')
OIDC_OP_AUTHORIZATION_ENDPOINT = f"{server_url}/realms/{realm}/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
...
```
These are the addresses Django uses to talk to Keycloak. Think of it like giving Django the phone number and address of Keycloak's office.

**E) Logging (lines 461-510)**
```python
'loggers': {
    'authentication': {
        'handlers': ['security_file', 'console'],
        'level': 'INFO',
    },
}
```
Two log files are created:
- `logs/django.log` — General errors and warnings
- `logs/security.log` — Login attempts, blocked access, suspicious activity

**How to read a security log entry:**
```
INFO ... OIDC claims received: {'sub': 'abc123', 'preferred_username': 'johndoe'}
WARNING ... OIDC: No user found for username=johndoe ... Access blocked.
```
This means: "Someone named johndoe tried to log in with a correct Keycloak password, but they don't have a Django user account yet."

---

### 4.4 `config/urls.py` — The Directory (169 lines)

**Purpose:** Maps every web address to the code that handles it.

**Think of it like a phone directory:**
```
"/"                         → dashboard_view
"/login/"                   → login_view
"/logout/"                  → logout_view
"/assets/"                  → asset_list_view
"/assets/create/"           → asset_create_view
"/assets/5/"                → asset_detail_view  (show asset with ID 5)
"/api/auth/login/"          → LoginAPIView
"/api/assets/"              → AssetListCreateAPIView
"/api/docs/"                → Swagger documentation page
```

**Why this matters:** When you type a URL in the browser, Django looks here first to find the matching code to run.

**Swagger setup (lines 59-80):**
```python
schema_view = get_schema_view(
    openapi.Info(
        title="GovAsset Platform API",
        description="REST API for the Government Asset Management Platform...",
    ),
    public=True,
)
```
This automatically generates documentation from the code itself. You don't have to write docs separately — Django reads your code and creates the documentation page.

---

### 4.5 `authentication/models.py` — The User Database Design (199 lines)

**Purpose:** Defines what a "user" looks like in the database.

**Three models (database tables) are defined here:**

**A) CustomUser — The User Account**
```python
class CustomUser(AbstractUser):
    role = models.CharField(max_length=20, choices=[...])
    ministry_schema = models.CharField(max_length=63, blank=True, null=True)
    keycloak_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
```
- **Why custom:** Django comes with a basic user model (username, password, email). We added: `role`, `ministry_schema`, `keycloak_id`, `phone`.
- **role:** Controls what you can see and do (5 roles from SUPER_ADMIN to AUDITOR).
- **ministry_schema:** Which ministry you belong to (e.g., `moh_schema`). Blank for Super Admin who sees everything.
- **keycloak_id:** Links this Django account to the Keycloak account.

**B) PendingAccess — The Waiting Room**
```python
class PendingAccess(models.Model):
    username = models.CharField(...)
    email = models.CharField(...)
    full_name = models.CharField(...)
    status = models.CharField(choices=["PENDING", "APPROVED", "REJECTED"])
    ...
```
**What it solves:** When someone logs in with a correct Keycloak password but has no Django account, they're put in a "waiting room." An admin must approve or reject them. This prevents random people from getting access.

**C) LoginAttempt — The Brute Force Shield**
```python
class LoginAttempt(models.Model):
    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
    username = models.CharField(...)
    ip_address = models.GenericIPAddressField(...)
    attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
```
**How it works:**
```
Wrong password attempt 1 → attempts = 1
Wrong password attempt 2 → attempts = 2
Wrong password attempt 3 → attempts = 3
Wrong password attempt 4 → attempts = 4
Wrong password attempt 5 → attempts = 5, locked_until = now + 15 min
Wrong password attempt 6 → blocked, "Account locked. 14 minutes remaining."
Successful login           → attempts reset to 0, lock removed
```

**Key code — is_locked property:**
```python
@property
def is_locked(self):
    if self.locked_until:
        from django.utils import timezone
        return timezone.now() < self.locked_until
    return False
```
This is like checking: "Is curfew still active?" If `locked_until` is in the future, the account is still locked.

---

### 4.6 `authentication/oidc_backend.py` — The Keycloak Bridge (146 lines)

**Purpose:** Handles the conversation between Django and Keycloak when someone logs in via the web.

**The three most important methods:**

**A) filter_users_by_claims() — "Do we know this person?"**
```python
def filter_users_by_claims(self, claims):
    keycloak_id = claims.get('sub')
    # Try to find user by Keycloak ID first
    users = self.UserModel.objects.filter(keycloak_id=keycloak_id)
    if users: return users
    
    # Not found by ID, try by username
    username = claims.get('preferred_username')
    users = self.UserModel.objects.filter(username=username)
    if users:
        user = users.first()
        user.keycloak_id = keycloak_id  # Link the accounts for next time
        user.save()
    return users
```
**Simple explanation:** When Keycloak says "this person is authenticated," we check: "Do we have a Django account for them?" First, we look by the Keycloak ID number. If not found, we try by their username. If we find them, we save the Keycloak ID so next time is faster.

**B) create_user() — "We don't know them — block and record"**
```python
def create_user(self, claims):
    PendingAccess.objects.create(
        username=claims.get('preferred_username'),
        email=claims.get('email', ''),
        full_name=claims.get('name', ''),
        keycloak_id=claims.get('sub', ''),
    )
    request.session['pending_access_notice'] = True
    return None  # Returning None means "login blocked"
```
Never automatically creates users. Instead creates a PendingAccess record and returns `None` which tells Django "deny login."

#### PendingAccess — The Full Picture

**The Critical Distinction — Authentication vs Authorization**

```
AUTHENTICATION = "Are you who you say you are?"
                  → Handled by Keycloak
                  → Checks username + password

AUTHORIZATION  = "Do you have permission to use THIS system?"
                  → Handled by Django
                  → Checks if a CustomUser profile exists
```

PendingAccess deals only with the second one. A person can pass authentication (Keycloak knows them) but fail authorization (Django has no profile for them).

**Scenario 1 — Wrong Password (Does NOT create PendingAccess)**

```
User types wrong password on Keycloak's login page
        ↓
Keycloak checks against its own user store
        ↓
Keycloak rejects immediately — "invalid credentials"
        ↓
Browser never even reaches Django
        ↓
NO PendingAccess record created
NO Django code runs at all
```

Keycloak handles wrong passwords entirely on its own.

**Scenario 2 — Correct Keycloak Login, No Django Profile (Creates PendingAccess)**

```
User types CORRECT password for a Keycloak account
        ↓
Keycloak verifies it successfully ✓
        ↓
Keycloak issues a token and redirects to Django's callback
        ↓
Django's GovAssetOIDCBackend.filter_users_by_claims() runs
        ↓
Searches CustomUser by keycloak_id → not found
Searches CustomUser by username → not found
        ↓
create_user() is called — does NOT auto-create the user
Instead creates a PendingAccess record:
    username, email, full_name, keycloak_id, status='PENDING'
        ↓
Returns None → login is BLOCKED
        ↓
User sees error: "Previous login attempt failed."
```

**Does this apply to mobile / API login?**

No. Mobile login (`POST /api/auth/login/`) never touches `GovAssetOIDCBackend`. It calls Django's `authenticate()` directly against the Django database. If the username does not exist in Django, it simply returns "Invalid username or password" — no PendingAccess record. PendingAccess is strictly a web SSO concept.

**Summary Table**

| Scenario | Where it's checked | PendingAccess created? |
|---|---|---|
| Wrong password on Keycloak page | Keycloak itself | No |
| Correct Keycloak password, no Django profile | Django's OIDC backend | Yes |
| Correct Keycloak password, Django profile exists | Django's OIDC backend | No — normal login |
| Wrong username/password on mobile API login | Django `authenticate()` directly | No |
| 5 failed Keycloak attempts (if Brute Force Detection enabled) | Keycloak itself | No — Keycloak locks account |

**C) update_user() — "We know them, update their info"**
```python
def update_user(self, user, claims):
    user.keycloak_id = claims.get('sub') or user.keycloak_id
    # Update role and ministry from Keycloak attributes
    attributes = claims.get('attributes', {})
    if attributes.get('role'):
        user.role = attributes['role'][0]
    if attributes.get('ministry_schema'):
        user.ministry_schema = attributes['ministry_schema'][0]
    user.save()
```
When an existing user logs in, we refresh their role and ministry from Keycloak. If an admin changed their role in Keycloak, it updates in Django too.

---

### 4.7 `authentication/api_views.py` — The Mobile Login System (473 lines)

**Purpose:** Handles login/logout for the mobile app (and any external system).

**Class overview:**

**A) LoginAPIView — The Main Login Endpoint**
```
POST /api/auth/login/
Body: {"username": "moh_admin", "password": "Admin@123"}
Response: {"access": "...jwt...", "refresh": "...", "role": "MINISTRY_ADMIN", ...}
```

**Step by step what happens (lines 67-218):**

1. **Check lockout:** `_is_locked_out(username, ip)` — Is this account currently locked?
2. **If locked:** Return HTTP 429 with minutes remaining
3. **Validate credentials:** Django checks username + password
4. **If wrong password:** `_record_failed_attempt(username, ip)` — Increment counter, possibly lock
5. **If correct password:** `_clear_failed_attempts(username, ip)` — Reset counter, generate JWT token
6. **Record audit:** Log the login event
7. **Return response:** Send back JWT token + user profile

**B) VerifyTokenAPIView — For Other Government Groups**
```
GET /api/auth/verify-token/
Header: Authorization: Bearer <token>
Response: {"valid": true, "role": "MINISTRY_ADMIN", "ministry_schema": "moh_schema", ...}
```
**Purpose:** Other groups (Group 2, Group 3, etc.) can call this to verify a user's identity. They send us a token, we decode it and tell them who the user is.

**C) LogoutAPIView — Ending the Session**
```python
def post(self, request):
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()  # Add to the blacklist
        # Record audit log
        return Response({"detail": "Logged out successfully"})
```
Adds the refresh token to a blacklist so it cannot be used again.

---

### 4.8 `authentication/api_permissions.py` — The API Bouncers (117 lines)

**Purpose:** Controls who can access each API endpoint. These are like bouncers at a club.

**The permission classes:**

| Class | What it allows | Example endpoint |
|-------|---------------|-----------------|
| `IsSuperAdmin` | Only SUPER_ADMIN | Creating ministries |
| `IsMinistryAdmin` | SUPER_ADMIN, MINISTRY_ADMIN | User management |
| `IsAgencyManagerOrAbove` | SUPER_ADMIN, MINISTRY_ADMIN, AGENCY_MANAGER | Viewing org chart |
| `CanManageAssets` | Everyone for reading. SUPER_ADMIN, MINISTRY_ADMIN, AGENCY_MANAGER, FACILITY_CLERK for writing. AUDITOR can only read. | Asset CRUD |
| `CanDeleteAssets` | Only SUPER_ADMIN, MINISTRY_ADMIN | Deleting assets |
| `CanViewAuditLogs` | SUPER_ADMIN, MINISTRY_ADMIN, AUDITOR | Viewing audit log |
| `HasMinistrySchema` | Anyone with ministry_schema set | Needs schema to operate |

**Key code — how they work (lines 30-50):**
```python
class CanManageAssets(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # AUDITOR can READ but not WRITE
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return request.user.role in ALL_ROLES  # Everyone can read
        return request.user.role in WRITE_ROLES    # Not auditor
```
"Safe" methods (GET/HEAD/OPTIONS) are allowed for everyone. Changing data (POST/PUT/DELETE) is restricted.

---

### 4.9 `authentication/decorators.py` — The Web Page Bouncers (73 lines)

**Purpose:** Controls who can access each web page (browser, not API).

**The decorators:**

**`@login_required_custom`:**
```python
def login_required_custom(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please log in first.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper
```
**What it does:** Checks if the user is logged in. If not, redirects to the login page with a message.

**`@role_required('MINISTRY_ADMIN', 'SUPER_ADMIN'):`**
Checks if the user has one of the allowed roles. If not, redirects with "You don't have permission."

**`@ministry_isolation_check:`**
Ensures the user has a ministry schema (except Super Admin who works across all ministries).

---

### 4.10 `authentication/middleware.py` — The Request Prepper (51 lines)

**Purpose:** This code runs on EVERY SINGLE REQUEST before the page loads.

```python
class SchemaMiddleware:
    def process_request(self, request):
        # Skip for public pages (login, logout, static files)
        if request.path.startswith(('/login/', '/logout/', '/static/', '/admin/')):
            return None
        
        if request.user.is_authenticated:
            request.schema_name = request.user.ministry_schema or 'public'
        else:
            request.schema_name = 'public'
```
**What it does:** Sets `request.schema_name` so every view knows which database schema to look in. For Super Admin → `'public'`. For ministry user → `'moh_schema'` etc.

---

### 4.11 `assets/models.py` — The Asset Database Design (245 lines)

**Purpose:** Defines what an "asset" looks like in the database.

**AssetCategory — Classifying Assets:**
```python
class AssetCategory(models.Model):
    name = models.CharField(max_length=200)      # "ICT Equipment"
    code = models.CharField(max_length=20, unique=True)  # "ICT"
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
```
Categories are like folders: ICT, VEH (Vehicles), FURN (Furniture), MED (Medical Equipment).

**Asset — The Main Model (all 245 lines):**
```python
class Asset(models.Model):
    # 1. IDENTIFICATION
    asset_number = models.CharField(max_length=50, unique=True)  # "MOH-ICT-2025-0001"
    name = models.CharField(max_length=300)                       # "Dell Latitude 5440"
    serial_number = models.CharField(...)
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT)
    
    # 2. MANUFACTURER & SUPPLIER
    manufacturer = models.CharField(...)    # "Dell"
    model_number = models.CharField(...)    # "Latitude 5440"
    supplier_name = models.CharField(...)   # "Dell Tanzania Ltd"
    purchase_order_number = models.CharField(...)  # "PO/MOH/2025/0842"
    
    # 3. LOCATION
    org_unit_id = models.IntegerField(...)       # Links to a facility
    org_unit_name = models.CharField(...)        # Snapshot: "Radiology Department"
    location_type = models.CharField(...)        # "Office Building"
    location_description = models.CharField(...) # "Block A, Room 204"
    
    # 4. STATUS
    status = models.CharField(choices=STATUS_CHOICES, default='ACTIVE')
    condition = models.CharField(choices=CONDITION_CHOICES, default='GOOD')
    
    # 5. DATES
    acquisition_date = models.DateField(...)     # When bought
    warranty_expiry_date = models.DateField(...) # When warranty ends
    asset_expiry_date = models.DateField(...)    # When it must be replaced
    
    # 6. FINANCIAL
    acquisition_cost = models.DecimalField(...)  # Price in TZS
    current_value = models.DecimalField(...)     # After depreciation
    
    # 7. PHOTO
    photo = models.ImageField(upload_to='assets/photos/')
```

**Important helper properties:**
```python
@property
def is_expired(self):
    """Is the asset past its expiry date?"""
    if self.asset_expiry_date:
        return self.asset_expiry_date < timezone.now().date()
    return False

@property
def expires_soon(self):
    """Does the asset expire within 90 days?"""
    if self.asset_expiry_date:
        days_left = (self.asset_expiry_date - timezone.now().date()).days
        return 0 <= days_left <= 90
    return False
```
These are used in the dashboard to show expiry warnings (red for expired, amber for soon).

---

### 4.12 `assets/api_views.py` — The Asset API for Mobile (628 lines)

**Purpose:** The mobile app uses this to list, create, update, and delete assets.

**AssetListCreateAPIView — The Main Asset API:**
```
GET /api/assets/?search=laptop&status=ACTIVE&category=ICT&condition=GOOD&page=1
→ Returns paginated list of assets matching filters

POST /api/assets/
→ Creates a new asset
Body: {"name": "Dell Laptop", "category_id": 1, ...}
```

**Key logic — Auto-generating asset numbers (lines 135-175):**
```python
def generate_asset_number(self, schema_name, category_code):
    # Format: MOH-ICT-2025-0001
    prefix = schema_name.replace('_schema', '').upper()[:3]
    year = str(timezone.now().year)
    base = f"{prefix}-{category_code}-{year}-"
    
    # Find the highest existing number and increment
    last_asset = Asset.objects.filter(
        asset_number__startswith=base
    ).order_by('asset_number').last()
    
    if last_asset:
        last_seq = int(last_asset.asset_number.split('-')[-1])
        new_seq = last_seq + 1
    else:
        new_seq = 1
    
    return f"{base}{new_seq:04d}"
```
Creates unique asset numbers like `MOH-ICT-2025-0001`, `MOH-ICT-2025-0002`, etc.

**Key logic — Schema isolation for Super Admin:**
```python
def get(self, request):
    if request.user.is_super_admin:
        return Response({
            "count": 0, "results": [],
            "detail": "Super Admin has no personal assets..."
        })
    
    schema_name = request.user.ministry_schema
    with schema_context(schema_name):
        # All queries here run in the correct schema
        queryset = Asset.objects.select_related('category').all()
        # Apply filters...
```
Super Admin gets an empty asset list because they don't belong to a ministry.

**Key logic — Update with field-level audit (lines 385-515):**
```python
def put(self, request, asset_id):
    with schema_context(schema_name):
        asset = get_object_or_404(Asset, id=asset_id)
        old_value = {
            'name': asset.name,
            'status': asset.status,
            'condition': asset.condition,
        }
        
        # Update only provided fields
        for field, value in data.items():
            if hasattr(asset, field):
                setattr(asset, field, value)
        asset.save()
        
        new_value = {
            'name': asset.name,
            'status': asset.status,
            'condition': asset.condition,
        }
        
        # Record WHAT changed
        AuditLog.objects.create(
            action='UPDATE',
            old_value=old_value,
            new_value=new_value,
            ...
        )
```
Before updating, we save a snapshot of the old values. After updating, we save the new values. Both go into the audit log so you can see exactly what changed.

---

### 4.13 `assets/views.py` — The Asset Web Pages (577 lines)

**Purpose:** The browser-based pages for managing assets (not the mobile app).

**Functions:**

| Function | URL | Purpose |
|----------|-----|---------|
| `asset_list_view` | `/assets/` | Shows a table of all assets with filter/search/pagination |
| `asset_create_view` | `/assets/create/` | Form to create a new asset |
| `asset_detail_view` | `/assets/5/` | Shows one asset's full details |
| `asset_edit_view` | `/assets/5/edit/` | Form to edit an asset |
| `asset_delete_view` | `/assets/5/delete/` | POST to delete an asset |

**generate_asset_number helper:**
Creates numbers like `MOH-ICT-2025-0001`. This is the same logic as in the API but used for the web forms.

**_load_asset_form_data helper:**
Loads all dropdown choices: categories, org units (facilities), funding sources, acquisition methods, location types, cost centres. This ensures the create/edit forms have all the options a user needs.

---

### 4.14 `organizations/models.py` — The Org Hierarchy + Audit (230 lines)

**Purpose:** Three important models.

**A) OrgUnit — The Organisation Tree:**
```python
class OrgUnit(models.Model):
    name = models.CharField(max_length=200)           # "Radiology Department"
    code = models.CharField(max_length=50, unique=True) # "RAD-001"
    unit_type = models.CharField(choices=[
        ('MINISTRY', 'Ministry'),
        ('AGENCY', 'Agency'),
        ('FACILITY', 'Facility'),
    ])
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True)
```
This creates a hierarchy:
```
Ministry of Health (MINISTRY)
    ├── Tanzania Medicines Authority (AGENCY)
    ├── Muhimbili Hospital (AGENCY)
    │   ├── Radiology Department (FACILITY)
    │   ├── Emergency Ward (FACILITY)
    │   └── Pharmacy (FACILITY)
    └── ...

Ministry of Finance (MINISTRY)
    ├── Tanzania Revenue Authority (AGENCY)
    └── ...
```

**B) MasterData — Reference Lists:**
```python
class MasterData(models.Model):
    CATEGORY_CHOICES = [
        ('FUNDING_SOURCE', 'Funding Source'),       # "Government Budget", "Donor Funded"
        ('ACQUISITION_METHOD', 'Acquisition Method'), # "Direct Purchase", "Donation"
        ('LOCATION_TYPE', 'Location Type'),          # "Office Building", "Warehouse"
        ('DISPOSAL_METHOD', 'Disposal Method'),      # "Auction", "Donation"
        ('COST_CENTRE', 'Cost Centre'),              # "ICT Department", "HR"
    ]
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    value = models.CharField(max_length=100)   # The code: "GOV_BUDGET"
    label = models.CharField(max_length=200)   # The display: "Government Budget"
```
**Purpose:** Instead of hardcoding options, we store them in the database. A Ministry Admin can add/edit/remove options without changing any code.

**C) AuditLog — The Immutable Record (lines 129-230):**
```python
class AuditLog(models.Model):
    performed_by_id = models.IntegerField(...)
    performed_by_name = models.CharField(max_length=200)
    action = models.CharField(choices=[
        'CREATE', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'ACCESS_DENIED'
    ])
    model_name = models.CharField(max_length=100)  # "Asset"
    object_id = models.CharField(max_length=50)     # "42"
    object_repr = models.CharField(max_length=200)  # "MOH-ICT-2025-0001 — Dell Laptop"
    old_value = models.JSONField(null=True)          # {"status": "ACTIVE"}
    new_value = models.JSONField(null=True)          # {"status": "UNDER_MAINTENANCE"}
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(...)
    user_agent = models.CharField(...)
```
**The tamper-proof mechanism (lines 183-200):**
```python
def save(self, *args, **kwargs):
    if self.pk is not None:  # If this record ALREADY EXISTS
        raise PermissionError("AuditLog cannot be modified!")
    super().save(*args, **kwargs)

def delete(self, *args, **kwargs):
    raise PermissionError("AuditLog cannot be deleted!")
```
**Simple explanation:** You can CREATE a new audit log entry, but you can NEVER edit or delete an existing one. If you try, Django throws an error. This makes the audit log legally acceptable as evidence.

---

### 4.15 `tenants/models.py` — The Ministry Blueprint (47 lines)

**Purpose:** Defines what a "ministry" is and how domain names map to schemas.

```python
class Ministry(TenantMixin):
    name = models.CharField(max_length=200)          # "Ministry of Health"
    short_name = models.CharField(max_length=50)     # "MOH"
    is_active = models.BooleanField(default=True)
    auto_create_schema = True  # Magic! Creates PostgreSQL schema automatically
```
**The magic of auto_create_schema:** When you save a new Ministry, django-tenants automatically:
1. Creates a new PostgreSQL schema: `moh_schema`
2. Runs all migrations inside that schema (creates all the tables)
3. Creates the Domain record for URL routing

```python
class Domain(DomainMixin):
    domain = models.CharField(max_length=253)  # "moh.localhost"
    ...
```
**URL routing:** When someone visits `moh.localhost:8000`, Django looks up this Domain record and routes them to the `moh_schema`.

---

### 4.16 `authentication/keycloak_admin.py` — Talking to Keycloak (295 lines)

**Purpose:** This code lets Django create, update, and delete users in Keycloak automatically.

**Key methods:**

**`_get_admin_token()`** — Django logs into Keycloak as admin:
```python
def _get_admin_token(self):
    response = requests.post(
        f"{self.server_url}/realms/master/protocol/openid-connect/token",
        data={
            'client_id': 'admin-cli',
            'username': config('KEYCLOAK_ADMIN_USERNAME'),
            'password': config('KEYCLOAK_ADMIN_PASSWORD'),
            'grant_type': 'password',
        }
    )
    return response.json()['access_token']
```

**`create_user()`** — Django creates a user in Keycloak:
```python
def create_user(self, username, email, first_name, last_name, password, role, ministry_schema):
    # Step 1: Create user
    response = requests.post(
        f"{self.server_url}/admin/realms/{self.realm}/users",
        headers={'Authorization': f'Bearer {token}'},
        json={
            'username': username,
            'email': email,
            'attributes': {
                'role': [role],
                'ministry_schema': [ministry_schema],
            }
        }
    )
    # Step 2: Get the user's UUID from the Location header
    keycloak_id = response.headers['Location'].split('/')[-1]
    
    # Step 3: Set password
    requests.put(
        f"{self.server_url}/admin/realms/{self.realm}/users/{keycloak_id}/reset-password",
        headers={'Authorization': f'Bearer {token}'},
        json={'type': 'password', 'value': password, 'temporary': False}
    )
    
    return keycloak_id
```
**What happens:** When an admin creates a user in the Django web interface, Django automatically creates the same user in Keycloak too. The admin doesn't need to go to Keycloak separately.

---

### 4.17 `authentication/user_views.py` — Admin User Management

**Purpose:** Web pages for managing users (create, edit, activate/deactivate, reset password).

| Page | What it does |
|------|-------------|
| `/users/` | Lists all users in the ministry |
| `/users/create/` | Creates a new user in BOTH Django AND Keycloak |
| `/users/5/edit/` | Edits user info (role, schema, name) |
| `/users/5/toggle-active/` | Enables or disables a user |
| `/users/5/reset-password/` | Resets password in BOTH Django AND Keycloak |

---

### 4.18 `authentication/dashboard_views.py` — The Home Page (145 lines)

**Purpose:** Shows statistics on the dashboard.

**Super Admin sees:**
- Total ministries
- Total users across all ministries
- Total assets across all ministries

**Ministry Admin sees:**
- Assets by status (Active, Under Maintenance, etc.)
- Expired assets (red warning)
- Assets expiring within 30 days (amber warning)
- Assets expiring within 31-90 days (yellow warning)
- Recent audit activity

**The expiry logic (lines 96-113):**
```python
for asset in expirable:
    days_left = (asset.asset_expiry_date - today).days
    if days_left < 0:
        expired_assets.append(asset)          # ALREADY expired — RED
    elif days_left <= 30:
        expiring_soon.append(asset)           # Within 30 days — AMBER
    elif days_left <= 90:
        expiring_later.append(asset)          # Within 90 days — YELLOW
```

---

### 4.19 `organizations/views.py` — Org Hierarchy + Audit Logs (403 lines)

**Purpose:** Web pages for viewing the org tree and audit logs.

**Org Unit List Page:**
Builds a tree structure like:
```
Ministry of Health
  ├── Tanzania Medicines Authority
  │   ├── HQ Office
  │   └── Lab Facility
  └── Muhimbili Hospital
      ├── Radiology Department
      ├── Emergency Ward
      └── Pharmacy
```

**Audit Log Page:**
Shows a paginated table of all actions with filters by action type (CREATE, UPDATE, DELETE, LOGIN, etc.).

---

### 4.20 `tenants/views.py` — Ministry Management (261 lines)

**Purpose:** Super Admin manages ministries here.

**Ministry Create Flow:**
```
Admin fills form: Name="Ministry of Health", Short Name="MOH", Schema="moh_schema"
    ↓
Validate schema name (must end with _schema)
    ↓
Create Ministry → auto_create_schema creates PostgreSQL schema + runs migrations
    ↓
Create Domain mapping (moh.localhost → moh_schema)
    ↓
Create root OrgUnit of type MINISTRY
    ↓
Done! The ministry is live.
```

---

### 4.21 `authentication/management/commands/setup_demo_data.py` — Demo Data (553 lines)

**Purpose:** One command to clean test data and seed professional-looking demo data.

**What it does:**

1. **Clean:** Deletes all test assets, audit logs, login attempts, pending access records
2. **Seed — Ministry of Health (9 assets):**
   - 4 ICT assets (Dell Laptop TSh 2.85M, HP Printer TSh 850K, Cisco Switch TSh 3.2M, Samsung TV TSh 1.8M)
   - 2 Vehicles (Toyota Land Cruiser TSh 85M, Toyota Hiace Ambulance TSh 65M)
   - 2 Medical (Mindray Analyzer TSh 45M, Philips Monitor TSh 38M)
   - 1 Furniture (Executive Desk Set TSh 4.5M)
3. **Seed — Ministry of Finance (4 assets):**
   - 2 ICT (HP EliteBook TSh 3.1M, Lenovo Desktop TSh 1.95M)
   - 1 Vehicle (Toyota Fortuner TSh 78M)
   - 1 Furniture (Conference Room Set TSh 6.2M)
4. **Create audit log entries** for each seed action

**Expected output:**
```
Cleaning test data...
  ✓ Cleared login attempts: X
  ✓ Cleared pending access: X
  ✓ Cleared X assets from moh_schema
  ✓ Cleared X audit logs from moh_schema
  ✓ Cleared X assets from mof_schema
  ✓ Cleared X audit logs from mof_schema
  Cleaning complete.

Seeding demo data...
  Seeding Ministry of Health (moh_schema)...
  ✓ Created 9 MOH assets

  Seeding Ministry of Finance (mof_schema)...
  ✓ Created 4 MOF assets
  Seeding complete.

✓ Demo data setup complete!
```

**Prerequisite:** This command requires `AssetCategory` codes to exist with values `ICT`, `VEH`, `FURN`, and a category containing "Medical" in the name. Verify with:
```python
# Inside python manage.py shell
from django_tenants.utils import schema_context
with schema_context('moh_schema'):
    from assets.models import AssetCategory
    for cat in AssetCategory.objects.all():
        print(cat.id, repr(cat.code), cat.name)
```

---

### 4.22 `config/wsgi.py` + `config/asgi.py` — Deployment Files

**WSGI (Web Server Gateway Interface):**
Used when deploying to a real server (Apache, Nginx). For production.

**ASGI (Asynchronous Server Gateway Interface):**
For future real-time features (notifications, WebSockets). Currently unused.

---

### 4.23 HTML Templates

**Purpose:** The visual pages that users see in their browser.

**How templates work:**
- `shared/base.html` — The main layout: header, sidebar, footer. ALL other pages "extend" this.
- Each page just fills in the content section.

**Example — asset_list.html:**
```html
{% extends "shared/base.html" %}
{% block content %}
<h1>Assets</h1>
<table>
  {% for asset in assets %}
    <tr>
      <td>{{ asset.asset_number }}</td>
      <td>{{ asset.name }}</td>
      <td>{{ asset.category.code }}</td>
      <td>{{ asset.status }}</td>
    </tr>
  {% endfor %}
</table>
{% endblock %}
```
This template loops through all assets and creates a table row for each one.

---

## 5. SECURITY FEATURES

This section explains every security measure in the project — this is a COMMON panel question.

### 5.1 Multi-Tenant Schema Isolation
**What:** Each ministry's data lives in a separate PostgreSQL schema.
**How:** `django-tenants` adds `SET search_path = moh_schema` before every database query.
**Why it matters:** Even if a user somehow bypasses the login checks, the database itself enforces separation. A query from MOH schema literally CANNOT see MOF data at the database level.

### 5.2 Role-Based Access Control (RBAC)
**What:** 5 user roles with different permissions.
**How:** Web pages use `@role_required()` decorators. API endpoints use DRF permission classes (`CanManageAssets`, `IsMinistryAdmin`, etc.).
**Why it matters:** A Facility Clerk cannot delete assets (only Ministry Admin can). An Auditor cannot create or edit anything (read-only).

### 5.3 Brute Force Lockout
**What:** Account locks after 5 wrong password attempts.
**How:** `LoginAttempt` model tracks attempts per username + IP. After 5 failures, `locked_until` is set to 15 minutes in the future. Every login check calls `_is_locked_out()` first.
**Why it matters:** Stops hackers from trying thousands of passwords.

### 5.4 Immutable Audit Log
**What:** Every action is recorded and can NEVER be edited or deleted.
**How:** The `save()` method raises `PermissionError` if the record already exists. The `delete()` method always raises `PermissionError`.
**Why it matters:** If someone tries to cover their tracks, the audit log is proof. This is legally defensible in court.

### 5.5 JWT Token Security
**What:** Login tokens expire after 30 minutes. Old tokens are blacklisted when refreshed.
**How:** `ACCESS_TOKEN_LIFETIME = 30 minutes`, `ROTATE_REFRESH_TOKENS = True`, `BLACKLIST_AFTER_ROTATION = True`.
**Why it matters:** Even if a token is stolen, it only works for 30 minutes. And you can't reuse an old refresh token.

### 5.6 Keycloak SSO
**What:** Users log in through Keycloak, not our Django code.
**How:** The OIDC flow redirects users to Keycloak's login page. Keycloak handles password verification. Django never touches the password.
**Why it matters:** If our Django server is compromised, the attacker still cannot steal passwords because we never had them.

### 5.7 Pending Access Approval
**What:** No account is ever auto-created. Every access must be approved by an admin.
**How:** When a Keycloak-authenticated user has no Django profile, `create_user()` in `oidc_backend.py` creates a `PendingAccess` record and returns `None` (blocked login).
**Why it matters:** Prevents unauthorized users from accessing the system even if they have valid Keycloak credentials.

### 5.8 Security Logging
**What:** All login attempts (successful and failed) are logged.
**How:** Python's logging module writes to `logs/security.log` in addition to the database audit log.
**Why it matters:** Two separate records of security events — one in the database, one in a file. If one is compromised, the other still provides evidence.

### 5.9 Security Headers
**What:** Django sends HTTP headers that protect against common web attacks.
**How:** Configured in `settings.py`:
- `SECURE_CONTENT_TYPE_NOSNIFF = True` — Prevents MIME-type sniffing
- `SECURE_BROWSER_XSS_FILTER = True` — Enables browser XSS filter
- `X_FRAME_OPTIONS = 'DENY'` — Prevents clickjacking
- `CSRF_COOKIE_SECURE = True` (in production) — CSRF token only sent over HTTPS
**Why it matters:** Protects against common web attacks like XSS, clickjacking, and MIME confusion.

### 5.10 Session Security
**What:** Browser sessions expire after 2 hours of inactivity.
**How:** `SESSION_COOKIE_AGE = 7200` (2 hours), `SESSION_EXPIRE_AT_BROWSER_CLOSE = True`.
**Why it matters:** If someone walks away from their computer, the session automatically expires.

---

## 6. HOW A REQUEST TRAVELS THROUGH THE SYSTEM

### Example: Mobile app logs in and views assets

```
Step 1: Phone sends POST request
        POST http://192.168.100.18:8000/api/auth/login/
        Body: {"username": "moh_admin", "password": "Admin@123"}
        
Step 2: Django receives the request
        ↓
        Middleware runs (TenantMainMiddleware, SchemaMiddleware)
        ↓
        URL router looks at /api/auth/login/ → matches LoginAPIView
        ↓
        LoginAPIView.post() runs:
        1. Check brute force lockout → Not locked
        2. authenticate(username, password) → Valid!
        3. Clear failed attempts
        4. Generate JWT token (includes role, ministry_schema)
        5. Record LOGIN in audit log
        6. Return token + user profile

Step 3: Phone receives response
        {"access": "eyJ...", "role": "MINISTRY_ADMIN", "ministry_schema": "moh_schema"}
        Phone stores the token

Step 4: Phone sends GET request for assets
        GET http://192.168.100.18:8000/api/assets/
        Header: Authorization: Bearer eyJ...
        
Step 5: Django receives the request
        ↓
        Middleware: SchemaMiddleware sets request.schema_name = "moh_schema"
        ↓
        URL router: /api/assets/ → AssetListCreateAPIView
        ↓
        Permission check: CanManageAssets → Allowed (GET is safe)
        ↓
        AssetListCreateAPIView.get():
        1. with schema_context("moh_schema"):  ← Switch to MOH's database schema
        2. Asset.objects.all() → Returns only MOH's assets
        3. Apply filters (search, status, category)
        4. Paginate (20 per page)
        5. Return JSON response

Step 6: Phone receives and displays the assets
```

### Example: Web browser logs in via Keycloak

```
Step 1: User visits http://localhost:8000/login/ → redirected to dashboard
        ↓
        Not logged in → redirected to login page
        ↓
        Clicks "Sign in with Government SSO" → goes to /oidc/authenticate/
        ↓
        Django redirects to Keycloak login page (http://localhost:8180/...)
        ↓
        User types username + password into KEYCLOAK's page (not Django's)

Step 2: Keycloak verifies password → Success!
        ↓
        Keycloak redirects back to Django: /oidc/callback/?code=XYZ123
        ↓
        Django's GovAssetOIDCBackend runs:
        1. filter_users_by_claims() → Searches for user
        2. User found → update_user() → Login successful
        3. User NOT found → create_user() → PendingAccess created → Login blocked

Step 3: Browser sees the dashboard (or "awaiting approval" page)
```

---

## 7. THE KEY COMMANDS

### Starting from scratch (new laptop)

```powershell
# Step 1: Install Python from python.org (check "Add to PATH")

# Step 2: Install PostgreSQL from postgresql.org

# Step 3: Clone or copy the project
cd D:\
git clone <repository-url> government_asset_platform

# Step 4: Create and activate virtual environment
cd D:\government_asset_platform
python -m venv venv
.\venv\Scripts\activate

# Step 5: Install all packages
pip install -r requirements.txt

# Step 6: Create the database in PostgreSQL
# Open pgAdmin → Create database → Name: government_assets_db

# Step 7: Run migrations (create all database tables)
python manage.py migrate_schemas --shared
# This creates tables in the public schema first

# Step 8: Create super admin account
python manage.py createsuperuser

# Step 9: Create a ministry
# Visit http://localhost:8000/ministries/create/
# Enter: Name="Ministry of Health", Schema="moh_schema"
# This automatically creates the schema + tables for MOH

# Step 10: Create demo data
python manage.py setup_demo_data

# Step 11: Start the server
python manage.py runserver 0.0.0.0:8000

# Step 12 (separate terminal): Start Keycloak
cd C:\keycloak\bin
kc.bat start-dev --http-port=8180
```

### Daily commands

```powershell
# Start Django
cd D:\government_asset_platform
.\venv\Scripts\activate
python manage.py runserver 0.0.0.0:8000

# Start Keycloak (for web login)
cd C:\keycloak\bin
kc.bat start-dev --http-port=8180

# Reset demo data
python manage.py setup_demo_data

# Make and apply database changes
python manage.py makemigrations
python manage.py migrate_schemas

# Open Python shell (for testing)
python manage.py shell

# Run automated tests
python manage.py test

# Create a new app
python manage.py startapp app_name
```

### Mobile app commands

```powershell
cd C:\Users\Hemed\govasset_mobile

# Install on connected phone
flutter run

# Build APK (to transfer manually)
flutter build apk --release
# Output: build\app\outputs\flutter-apk\app-release.apk
```

---

## 8. COMMON PANEL QUESTIONS AND ANSWERS

### Q: What problem does this system solve?
**A:** Before this system, government ministries tracked assets on paper and Excel sheets — data was lost, there was no visibility, and auditing was impossible. Our platform provides a centralized, secure, multi-tenant system where each ministry tracks their assets from acquisition to disposal, with role-based access, tamper-proof audit trails, and both web and mobile interfaces.

### Q: What technologies did you use and why?
**A:** Django (Python) for the backend because it's the most popular framework for government systems with built-in security. PostgreSQL because its schema feature enables multi-tenancy — each ministry's data is isolated at the database level. django-tenants for automatic schema management. Keycloak for SSO — users log in through a separate secure system rather than our code handling passwords. Flutter for the mobile app — one codebase works on both Android and iPhone. JWT tokens for secure mobile authentication with automatic expiration.

### Q: How does multi-tenancy work?
**A:** When a new ministry is created, django-tenants automatically creates a separate PostgreSQL schema (like a folder) for that ministry. All user accounts live in a shared "public" schema, but assets, organizations, and audit data are stored in each ministry's private schema. When a user logs in, our middleware detects their ministry and switches the database connection to their schema. Even at the database level, one ministry cannot see another's data.

### Q: What security features have you implemented?
**A:** Nine security measures: (1) Keycloak SSO — passwords never handled by our code, (2) Role-based access — 5 roles control what users see and do, (3) Brute-force lockout — 5 wrong attempts lock the account for 15 minutes, (4) Immutable audit log — no one can edit or delete audit entries, (5) JWT token security — tokens expire in 30 minutes and old tokens are blacklisted, (6) Pending access approval — no accounts are auto-created, (7) Dual logging — security events recorded in both database and file, (8) Security headers — protection against XSS, clickjacking, and MIME attacks, (9) Session timeout — automatic logout after 2 hours of inactivity.

### Q: How is the mobile app different from the web?
**A:** The web uses Keycloak SSO — users are redirected to Keycloak's page to log in. The mobile app sends credentials directly to our Django API, which validates them and returns a JWT token. The mobile app doesn't use Keycloak because opening a browser page on a phone during login feels clunky. Both methods produce the same JWT token with the same user information — only the route is different.

### Q: How does the audit trail work?
**A:** Every action (login, create asset, update asset, delete asset) is recorded in the AuditLog table with: who did it, what they did, when, from which IP address, what the old value was, and what the new value was. The AuditLog model overrides the save() and delete() methods to prevent any modification or deletion of existing records. Even the Super Admin cannot edit or delete an audit log entry.

### Q: How would you scale this for 20+ ministries?
**A:** The system is already designed for this — just use the ministry creation form to add new ministries. Each new ministry gets its own schema automatically. For performance, we would add database indexes, implement caching (Redis), and potentially use read replicas for the audit log queries. The current architecture supports hundreds of schemas without modification.

### Q: What happens if someone tries to hack the login?
**A:** For the web: Keycloak has its own brute force detection — it locks the account after 5 failed attempts. For the mobile API: Our Django code tracks attempts per username + IP address. After 5 failures, the account is locked for 15 minutes. The lockout is tracked in a database table and checked before every login attempt. Additionally, all failed attempts are logged to both the database audit log and a text file.

### Q: What happens if you lose the database?
**A:** We follow the standard backup procedure: (1) Daily PostgreSQL dumps using `pg_dump`, (2) The audit log files are also written to text files in the `logs/` directory, (3) The `.env` file with passwords is backed up separately. With a recent database dump and the `.env` file, we can restore the entire system on a new machine in under an hour.

### Q: What is the difference between authentication and authorization?
**A:** Authentication is "are you who you say you are?" — it's the username and password check, handled by Keycloak for web users and Django for mobile users. Authorization is "what are you allowed to do?" — it's the role check, handled by our decorators and permission classes. A user can be authenticated (have a valid password) but denied authorization (no Django profile). This is exactly what PendingAccess handles.

### Q: How did you structure the database for multi-tenancy?
**A:** We use django-tenants, which separates apps into two groups: SHARED_APPS (user accounts, ministry records) live in one main "public" schema accessible to all. TENANT_APPS (assets, organizations, audit logs) are duplicated into each ministry's own schema. When a query runs, the database engine automatically sets the search path to the correct schema based on the logged-in user. The schemas are created automatically when a ministry is added through the web interface.

---

## QUICK REFERENCE — FILES AND THEIR JOBS

| File | One-sentence job |
|------|-----------------|
| `.env` | Stores all passwords and secret keys |
| `manage.py` | The command centre — run all commands through this |
| `config/settings.py` | Every configuration setting for the entire project |
| `config/urls.py` | Maps every web address to the code that handles it |
| `authentication/models.py` | Defines User, PendingAccess, and LoginAttempt in the database |
| `authentication/views.py` | Login and logout web pages |
| `authentication/api_views.py` | Login and logout for the mobile app |
| `authentication/oidc_backend.py` | Connects Django to Keycloak for SSO |
| `authentication/keycloak_admin.py` | Creates and manages users in Keycloak |
| `authentication/decorators.py` | Checks user roles before showing web pages |
| `authentication/api_permissions.py` | Checks user roles before allowing API calls |
| `authentication/middleware.py` | Runs on every request — sets the database schema |
| `authentication/dashboard_views.py` | Shows statistics on the home page |
| `authentication/user_views.py` | Web pages for creating/editing users |
| `authentication/pending_access_views.py` | Web pages for approving blocked users |
| `assets/models.py` | Defines Asset and AssetCategory in the database |
| `assets/views.py` | Web pages for managing assets |
| `assets/api_views.py` | Asset management for the mobile app |
| `organizations/models.py` | Defines OrgUnit, MasterData, and AuditLog |
| `organizations/views.py` | Web pages for org hierarchy and audit logs |
| `organizations/api_views.py` | Org hierarchy and dashboard for the mobile app |
| `organizations/master_data_views.py` | Web pages for managing reference data |
| `tenants/models.py` | Defines Ministry and Domain |
| `tenants/views.py` | Web pages for Super Admin to manage ministries |
| `authentication/management/commands/setup_demo_data.py` | Creates demo data for presentations |
| `templates/shared/base.html` | The main page layout — everything else extends this |
| `static/css/style.css` | The visual design of the entire website |
| `logs/security.log` | Record of login attempts and blocked access |
| `logs/django.log` | Record of errors and warnings |
| `requirements.txt` | List of all packages to install |

---

## WHO TO REFER TO FOR WHAT QUESTIONS

| Question topic | File to look at |
|---------------|----------------|
| Project overview | This document |
| Settings and config | `config/settings.py` |
| How users work | `authentication/models.py` |
| How login works (web) | `authentication/views.py` + `authentication/oidc_backend.py` |
| How login works (mobile) | `authentication/api_views.py` |
| How assets work | `assets/models.py` + `assets/views.py` + `assets/api_views.py` |
| How security works | `authentication/decorators.py` + `authentication/api_permissions.py` + `authentication/middleware.py` |
| How audit trail works | `organizations/models.py` (AuditLog section) |
| How ministries work | `tenants/models.py` + `tenants/views.py` |
| How the API works | `config/urls.py` + `authentication/api_urls.py` |
| How demo data works | `authentication/management/commands/setup_demo_data.py` |
| How the mobile app connects | `authentication/api_views.py` |
| How Keycloak works | `authentication/oidc_backend.py` + `authentication/keycloak_admin.py` |
| How the org chart works | `organizations/models.py` (OrgUnit) + `organizations/views.py` |
| How master data works | `organizations/models.py` (MasterData) + `organizations/master_data_views.py` |

---

## APPENDIX A — TEST USERS

All users use password `Admin@123`:

| Username | Expected Result |
|---|---|
| `superadmin` | Dashboard shows Platform Overview, no ministry schema |
| `moh_admin` | Dashboard shows `moh_schema` |
| `mnh_manager` | Dashboard shows `moh_schema` |
| `rad_clerk` | Dashboard shows `moh_schema` |
| `moh_auditor` | Dashboard shows `moh_schema` |
| `mof_admin` | Dashboard shows `mof_schema` |

---

## APPENDIX B — INSTALLING THE FLUTTER APP ON ANDROID

### B.1 Connect and run directly via USB

1. Enable **Developer Options** and **USB Debugging** on your phone.
2. Connect the phone via USB.
3. Verify Flutter detects it: `flutter devices`
4. Install and launch: `flutter run`
5. If multiple devices: `flutter run -d <device_id>` (get ID from `flutter devices`)

### B.2 Build an APK for manual install

```bash
flutter build apk --release
```

APK location: `build/app/outputs/flutter-apk/app-release.apk`

Transfer the APK to your phone and tap to install. You may need to allow "Install unknown apps" in Android settings.

### B.3 Build for Play Store submission

```bash
flutter build appbundle
```

Output: `build/app/outputs/bundle/release/app-release.aab` (upload this to the Play Store).

---

## APPENDIX C — TESTING WITH SWAGGER

1. Start Django: `python manage.py runserver 0.0.0.0:8000`
2. Open `http://localhost:8000/api/docs/`
3. First, hit `POST /api/auth/login/` with your credentials to get a token.
4. Copy the `access` token (without quotes).
5. Click **Authorize** and enter: `Bearer <your_token>`
6. Now test any endpoint:

| Endpoint | Expected result |
|---|---|
| `GET /api/assets/` | 200 with asset list |
| `GET /api/dashboard/stats/` | 200 with statistics |
| `GET /api/org-units/` | 200 with hierarchy |
| `GET /api/audit-logs/` | 200 with logs |
| `GET /api/auth/verify-token/` | 200 with user info |

---

## APPENDIX D — IP CHANGE CHECKLIST

Every time you reconnect to a different WiFi/hotspot, your laptop gets a new IP. Update everything:

**D.1 Find your new IP**
```bash
ipconfig
```
Look for **IPv4 Address** under your hotspot or WiFi adapter.

**D.2 Update Flutter**
Open `C:\Users\Hemed\govasset_mobile\lib\config\api_config.dart` and change `serverIp` to your new IP. Then reinstall:
```bash
flutter run
```

**D.3 Update ALLOWED_HOSTS**
In `config/settings.py`, add the new IP to `ALLOWED_HOSTS`.

**D.4 Register the domain**
Use the shell command (or Django admin) to register the new IP as a domain for the relevant schema.

**D.5 Verify everything**
- `python manage.py runserver 0.0.0.0:8000`
- `kc.bat start-dev --http-port=8180`
- Browser: `http://localhost:8000`
- Swagger: `http://localhost:8000/api/docs/`
- Phone: login works
