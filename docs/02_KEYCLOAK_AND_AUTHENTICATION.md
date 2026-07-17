# GOVERNMENT ASSET PLATFORM — Keycloak & Authentication

> **Purpose:** Everything about authentication — Keycloak SSO, JWT tokens, Django ↔ Keycloak sync, API integration for external systems, and security features.
> **For:** Panel defense, external system integration, daily admin tasks.

---

## Table of Contents

- [1. What Keycloak Is & Why We Use It](#1-what-keycloak-is--why-we-use-it)
- [2. Authentication vs Authorization](#2-authentication-vs-authorization)
- [3. The Two Authentication Paths](#3-the-two-authentication-paths)
- [4. Keycloak Admin Console — Complete Walkthrough](#4-keycloak-admin-console--complete-walkthrough)
- [5. Django ↔ Keycloak Sync Architecture](#5-django--keycloak-sync-architecture)
- [6. Custom Attributes (role & ministry_schema)](#6-custom-attributes-role--ministry_schema)
- [7. SSO Login Flow — Step by Step](#7-sso-login-flow--step-by-step)
- [8. API Login Flow (JWT) — Step by Step](#8-api-login-flow-jwt--step-by-step)
- [9. JWT Tokens Explained](#9-jwt-tokens-explained)
- [10. Security Features](#10-security-features)
- [11. External System Integration — Direct API](#11-external-system-integration--direct-api)
- [12. External System Integration — SSO Redirect](#12-external-system-integration--sso-redirect)
- [13. Complete API Endpoint Reference](#13-complete-api-endpoint-reference)
- [14. Test Accounts](#14-test-accounts)

---

## 1. What Keycloak Is & Why We Use It

**Keycloak is a separate authentication server.** It handles passwords so Django NEVER stores them.

| Approach | Who stores passwords | Risk |
|----------|-------------------|------|
| Django login only | Django | If Django gets hacked, ALL passwords are leaked |
| Keycloak SSO (ours) | Keycloak only | If Django gets hacked, passwords are still safe |

**Our division of responsibility:**

| System | Handles | Purpose |
|--------|---------|---------|
| **Keycloak** | Username, password, email, custom attributes (`role`, `ministry_schema`), `enabled` status | **Identity** — "Who are you?" |
| **Django** | Role (SUPER_ADMIN → AUDITOR), `ministry_schema`, `is_locked` (brute-force), permissions | **Authorization** — "What can you do?" |

**Keycloak URLs:**
- Local admin console: `http://localhost:8180/admin`
- Railway admin console: `https://keycloak-production-4f96.up.railway.app/admin`
- Realm: `govasset` (NOT `master`)
- Admin login: `superadmin` / `Admin@123`

---

## 2. Authentication vs Authorization

**Authentication = Who are you?** (Login — prove your identity)

**Authorization = What can you do?** (Permissions — what you're allowed to access)

```
Authentication FIRST:
  User presents credentials → Keycloak verifies → "You are moh_admin"

Authorization SECOND:
  System checks: "Is moh_admin allowed to DELETE assets?"
  Checks role: MINISTRY_ADMIN → YES
  Checks ministry_schema: moh_schema → YES
  → Action allowed!
```

In our code:
- Authentication → `oidc_backend.py` (SSO) or `auth_backend.py` (API)
- Authorization (web) → `@role_required('MINISTRY_ADMIN')` decorators
- Authorization (API) → Permission classes like `CanManageAssets`, `IsSuperAdmin`

---

## 3. The Two Authentication Paths

### Path 1: Web Browser (SSO via Keycloak)

```
1. User visits dashboard → redirected to Keycloak login page
2. User types username/password on Keycloak's page (NOT Django's)
3. Keycloak verifies → redirects back to Django with auth code
4. Django exchanges code for user info → creates session cookie
5. User is logged in — Django NEVER saw the password
```

### Path 2: Mobile App / External System (Direct API)

```
1. Flutter sends: POST /api/auth/login/
   {"username": "moh_admin", "password": "Admin@123"}
2. Django auth_backend checks credentials via Keycloak REST API
3. If valid → returns JWT tokens: { "access": "eyJ...", "refresh": "eyJ..." }
4. Flutter stores JWT, sends with every API call:
   Authorization: Bearer eyJ...
```

---

## 4. Keycloak Admin Console — Complete Walkthrough

### 4.1 Realm Dropdown (Top-Left)

Switch between realms. We use two:

| Realm | Purpose | When to use |
|-------|---------|-------------|
| **master** | Admin realm — manages Keycloak server itself | Only when managing Keycloak itself (rare) |
| **govasset** | **Our realm** — application users live here | Day-to-day work: CRUD users, clients, config |

> ⚠️ **If you can't find a user/client** — you're probably in the wrong realm. Switch to `govasset`.

### 4.2 Clients

Each application that uses Keycloak needs a client.

| Our Client | Type | Who uses it |
|------------|------|-------------|
| `govasset-django` | Ours | Our Django application (SSO) |
| `group2-app` | Ours | External system integration |
| `account-console` | Built-in | "Manage Account" page |
| `account` | Built-in | Account management API |
| `admin-cli` | Built-in | Admin API scripts |
| `realm-management` | Built-in | Internal Keycloak management |
| `security-admin-console` | Built-in | The admin console itself |
| `broker` | Built-in | Identity brokering |

**Key client settings:**

| Setting | What it does | Our value |
|---------|-------------|-----------|
| **Client ID** | Unique name | `govasset-django` |
| **Client authentication** | ON = needs secret | ON for server apps |
| **Standard flow** | Authorization Code flow | ON (for SSO) |
| **Direct access grants** | Resource Owner flow | ON (for API login) |
| **Valid Redirect URIs** | Where users CAN be redirected after login | `https://our-app.com/*` |
| **Web origins** | Allowed CORS domains | `https://our-app.com` |
| **Root URL** | Base URL | `https://our-app.com` |

### 4.3 Users

| Field | What it is |
|-------|-----------|
| **Username** | Login name (must be unique) |
| **Email** | User's email (optional but recommended) |
| **Email verified** | Whether they confirmed their email |
| **First name / Last name** | Display name |
| **Required user actions** | Actions user MUST do on next login (e.g., "Update Password") |
| **Attributes tab** | **IMPORTANT** — Set `role` and `ministry_schema` custom attributes here |

**Creating a user:**
1. Users → Add user → Username → Save
2. Credentials → Set password → Enter password → Temporary: OFF
3. **Attributes tab** → Add `role` (e.g., `MINISTRY_ADMIN`) and `ministry_schema` (e.g., `moh_schema`)
4. The user must ALSO exist in Django — create via Django admin or `setup_demo_data`

### 4.4 Sessions

Shows who is currently logged in. You can:
- View active sessions (user, IP, start time, last access)
- Log out a specific user (immediate — no warning)
- Log out ALL users (after critical security changes)

### 4.5 Events

Two types:

| Event Type | What it records | Example |
|-----------|----------------|---------|
| **Login events** | User login attempts | LOGIN (success), LOGIN_ERROR (failure), LOGOUT |
| **Admin events** | Admin actions | Create user, update client, delete role |

Common `LOGIN_ERROR` reasons:
- `invalid_user_credentials` → wrong password
- `user_not_found` → username doesn't exist
- `user_disabled` → account is disabled

### 4.6 Security Defenses

Brute force detection settings:

| Setting | Our value |
|---------|-----------|
| Max login failures | 5 |
| Wait increment | 15 minutes |
| Permanent lockout | ON (admin must unlock) |

### 4.7 Authentication (Flows)

Controls HOW users log in:
- **Browser flow** — Web login (steps: cookie check → username/password form → OTP if needed)
- **Direct grant flow** — API login (username+password directly)
- **Required Actions** — Force password change, set up 2FA
- **Password Policy** — Min length, require digits/special chars

### 4.8 Other Sidebar Items

| Item | When we use it |
|------|---------------|
| **Client Scopes** | Rare — only if we need extra info in tokens |
| **Realm Roles** | Rare — we map Django roles, not Keycloak roles |
| **Groups** | Rare — we assign roles individually |
| **Identity Providers** | Never — our Keycloak is the source of truth |
| **User Federation** | Never — users are created directly in Keycloak |
| **Server Info** | Check version, verify PostgreSQL connection, check memory |

---

## 5. Django ↔ Keycloak Sync Architecture

Your application has **two separate user databases** that must stay in sync:

| Database | Where it lives | What it stores | Purpose |
|----------|---------------|----------------|---------|
| **Keycloak** | Railway PostgreSQL (or local H2) | Username, password, email, `role`+`ministry_schema` (attributes), `enabled` | **Identity** — password verification, SSO login |
| **Django** | Railway PostgreSQL → `public.authentication_customuser` | Username, `role`, `ministry_schema`, `is_active`, `is_locked`, `keycloak_id` | **Authorization** — dashboard access, permissions |

**Every logged-in user exists in BOTH databases.** They must be kept consistent — if you deactivate in Django but not Keycloak, they can still SSO login.

### 5.1 Key Files for Sync

| File | Purpose |
|------|---------|
| `authentication/oidc_backend.py` | **The bridge** — runs on EVERY SSO login. Syncs `is_active` FROM Keycloak, syncs `role`/`ministry_schema` FROM Keycloak claims to Django. |
| `authentication/keycloak_admin.py` | **Admin API client** — talks to Keycloak's REST API. Used for activate/deactivate, create user, reset password. |
| `authentication/user_views.py` | **Web views** — sync changes BOTH ways when admins manage users. |
| `authentication/management/commands/setup_demo_data.py` | Creates demo users in BOTH databases. |
| `authentication/management/commands/sync_keycloak_attributes.py` | One-time fix to push `role`/`ministry_schema` to existing Keycloak users. |

### 5.2 Complete Sync Flows

**Login Flow (SSO) — Auto-syncs FROM Keycloak to Django:**
```
User types username/password → Keycloak verifies
        │
        ▼
OIDC callback to Django → filter_users_by_claims()
  ├── User found in Django?
  │   ├── YES → Sync is_active FROM Keycloak (if disabled in Keycloak → disabled in Django)
  │   └── NO  → Create PendingAccess record → login denied: "pending approval"
  │
  ▼
update_user() → Sync role + ministry_schema FROM Keycloak claims TO Django
  (This is why custom attributes in Keycloak are essential!)
  │
  ▼
get_user() → Final gate
  ├── is_active=True AND is_locked=False → GRANT ACCESS
  ├── is_locked=True → BLOCK: "account locked"
  └── is_active=False → BLOCK: "account deactivated"
```

**Activate/Deactivate Flow (Django → Keycloak):**
```
Admin clicks "Activate" or "Deactivate" on user page
        │
        ▼
user_toggle_active_view()
  1. Toggle user.is_active in Django database
  2. Call kc.update_user(is_active=...) → PUT to Keycloak API
```

**Create User Flow (Django admin → Both):**
```
Admin fills form and submits
        │
        ▼
user_create_view()
  1. kc.create_user() — create in Keycloak FIRST
     ├── Success → returns keycloak_id UUID
     └── Fail → show error, STOP (don't create Django user)
  2. CustomUser.objects.create_user() — create in Django
     ├── Success → done
     └── Fail → kc.delete_user() ROLLBACK Keycloak (cleanup!)
```

### 5.3 Troubleshooting Sync Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| "Status updated in system but Keycloak sync failed: 401" | Wrong admin credentials | Set `KEYCLOAK_ADMIN_USERNAME`/`PASSWORD` env vars |
| User can log in but gets PendingAccess | User in Keycloak but not Django | Approve PendingAccess in Django admin |
| User logs in but has no permissions | `role`/`ministry_schema` missing in Keycloak | Run `sync_keycloak_attributes` command |
| User deactivated in Django but can still log in | Keycloak's `enabled` still true | Toggle from Django user management |
| 502 errors in Keycloak | Out of memory | Set `JAVA_OPTS_APPEND=-Xmx256m -Xms128m` |

---

## 6. Custom Attributes (role & ministry_schema)

### 6.1 What They Are

Django needs two pieces of info that Keycloak doesn't know by default:

- **`role`** — Permission level: `SUPER_ADMIN`, `MINISTRY_ADMIN`, `AGENCY_MANAGER`, `FACILITY_CLERK`, `AUDITOR`
- **`ministry_schema`** — Which ministry's data: `moh_schema`, `mof_schema` (blank for SUPER_ADMIN)

These are stored as **Keycloak custom attributes** on each user. On every SSO login, `update_user()` reads them from the token and syncs them to Django.

### 6.2 How to Set Them

| Method | How |
|--------|-----|
| `setup_demo_data --sync-keycloak` | Auto-sets both on user creation (called from user_create_view) |
| `sync_keycloak_attributes` | One-time fix pushes attributes to existing Keycloak users |
| Keycloak admin console → User → Attributes tab | Manual — add `role` and `ministry_schema` as key-value pairs |

### 6.3 Keycloak 26+ Requirement (Important!)

In Keycloak 26+, custom attributes are **silently dropped** unless first **declared** in the realm's **User Profile** configuration. If you try to set an undeclared attribute via the API, Keycloak returns 204 but doesn't save it.

**The fix:** `ensure_custom_attributes_defined()` in `keycloak_admin.py` (line 222):
1. Fetches current user profile config via `GET /admin/realms/{realm}/users/profile`
2. Checks if `role` and `ministry_schema` are already listed
3. If missing, adds them via `PUT /admin/realms/{realm}/users/profile`

This is called automatically by `setup_demo_data` and `sync_keycloak_attributes`.

---

## 7. SSO Login Flow — Step by Step

```
1. User visits Django website (e.g., http://localhost:8000/dashboard/)
        │
2. Django sees user is not logged in → redirects to Keycloak:
   GET http://localhost:8180/realms/govasset/protocol/openid-connect/auth
   ?client_id=govasset-django
   &redirect_uri=http://localhost:8000/oidc/callback/
   &response_type=code
   &scope=openid profile email
        │
3. Keycloak shows login page — user types credentials
        │
4. Keycloak verifies credentials:
   ├── INVALID → show error on Keycloak page
   └── VALID → redirects to Django callback URL with auth code:
       GET http://localhost:8000/oidc/callback/?code=abc123
        │
5. Django receives callback → exchanges code for tokens:
   POST http://localhost:8180/realms/govasset/protocol/openid-connect/token
   grant_type=authorization_code
   &code=abc123
   &redirect_uri=http://localhost:8000/oidc/callback/
        │
6. Django receives ID token + access token
   Decodes ID token → gets user info (username, email, role, ministry_schema)
        │
7. OIDC backend runs:
   filter_users_by_claims() → find user in Django
   update_user() → sync role/ministry_schema FROM token
   get_user() → check is_locked + is_active
        │
8. User is logged in → redirect to dashboard
   Django creates session cookie → browser remembers login
   │
   │ (If user NOT in Django → PendingAccess record created → login denied)
```

---

## 8. API Login Flow (JWT) — Step by Step

```
1. Flutter app sends: POST /api/auth/login/
   {"username": "moh_admin", "password": "Admin@123"}
        │
2. Django receives request → LoginAPIView runs
        │
3. Check brute-force lockout:
   ├── LOCKED → return 429: "Too many attempts. Wait 15 minutes."
   └── NOT LOCKED → continue
        │
4. APIAuthBackend.authenticate() → calls Keycloak:
   POST http://localhost:8180/realms/govasset/protocol/openid-connect/token
   grant_type=password
   &client_id=govasset-django
   &username=moh_admin
   &password=Admin@123
        │
5. Keycloak verifies:
   ├── VALID → returns access token → Django finds/creates user
   └── INVALID → return None → LoginAPIView records failed attempt
        │
6. If success → clear failed attempts, create JWT pair, log AuditLog
        │
7. Return: {"access": "eyJ...", "refresh": "eyJ...", "user": {...}}
        │
8. Flutter stores tokens → sends access token with every API call:
   Authorization: Bearer eyJ...
        │
9. When access token expires (30 min) → Flutter calls:
   POST /api/auth/refresh/  {"refresh": "eyJ..."}
   → Returns new access + refresh tokens
```

---

## 9. JWT Tokens Explained

### 9.1 What Is a JWT?

**JWT = JSON Web Token.** A digital ID card with a cryptographic signature. Contains user info (role, ministry) and is signed so it cannot be tampered with.

**Analogy — Hotel key card:**
- The key card proves you're a guest (authentication)
- It only opens YOUR room (authorization)
- It expires at checkout (token expiry)

### 9.2 Token Structure

```
Access Token:   Lifespan = 30 minutes
Refresh Token:  Lifespan = 24 hours
```

A JWT has 3 parts separated by dots:
```
header.payload.signature
eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.xY7g...
```

- **Header** — Algorithm info (HMAC-SHA256)
- **Payload** — User data (username, role, ministry_schema, exp, iat) — BASE64 encoded, NOT encrypted
- **Signature** — Verifies token hasn't been tampered with

### 9.3 Access Token vs Refresh Token

| Token | Lifespan | What it can do | Why separate? |
|-------|----------|----------------|---------------|
| **Access** | 30 minutes | Access any API endpoint | Short lifespan limits damage if stolen |
| **Refresh** | 24 hours | ONLY get new access tokens | Long lifespan for good UX |

### 9.4 Token Security Features

- **Token rotation:** Each refresh gives a NEW refresh token. Old one is blacklisted.
- **Blacklisting:** Used tokens are blacklisted — they cannot be reused even if valid.
- **Logout:** Explicitly blacklists the token.
- **Signature:** Tokens are signed with Django's SECRET_KEY — cannot be forged.

### 9.5 Configuring Token Lifetimes

In `config/settings.py`:
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
```

### 9.6 Common JWT Confusions

| Misconception | Truth |
|--------------|-------|
| "JWT is the login system" | JWT is the OUTPUT of login. Login is credential verification. |
| "JWT content is encrypted" | The payload is BASE64-encoded, NOT encrypted. Anyone can decode and read it. Only the signature prevents tampering. |
| "JWT is like a password" | JWT expires in 30 minutes. Password lasts forever. JWT is sent on every request. Password is sent once during login. |

---

## 10. Security Features

### 10.1 Nine Layers of Security

| Layer | What it protects | How |
|-------|-----------------|-----|
| 1. HTTPS/TLS | Data in transit | Railway provides auto-HTTPS |
| 2. Schema isolation | Cross-ministry data access | Each ministry in its own PG schema |
| 3. Role-Based Access (RBAC) | Unauthorized actions | 5 roles with different permissions |
| 4. JWT security | API token theft | 30-min expiry, rotation, blacklisting |
| 5. Keycloak SSO | Password storage | Django NEVER stores passwords |
| 6. Brute-force protection | Account guessing | 5 failures → 15-min lockout → permanent disable |
| 7. Immutable audit log | Evidence tampering | Cannot edit or delete existing records |
| 8. Pending access approval | Unauthorized account creation | Every new user must be approved by admin |
| 9. Security headers + logging | XSS, clickjacking, CSRF | Headers + dual logging (django.log + security.log) |

### 10.2 Brute-Force Lockout — How It Works

```
1st failed login → Create LoginAttempt record
2nd failure → Increment attempts counter
...
5th failure → Set stage = "LOCKED", locked_until = now + 15 min
After 15 min → Cooldown expires → Counter resets
After 10 total failures → Account permanently disabled (is_active = False)
Unlock link sent to email OR admin can unlock manually
```

**Code location:** `authentication/models.py`, `authentication/auth_backend.py`

### 10.3 Immutable Audit Log

```python
class AuditLog(models.Model):
    def save(self, *args, **kwargs):
        if self.pk is not None:  # This record ALREADY exists
            raise PermissionError("Audit log records cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit log records cannot be deleted.")
```

**What this means:**
- ✓ You CAN create new audit logs (every action logs automatically)
- ✗ You CANNOT edit existing audit logs (raises PermissionError)
- ✗ You CANNOT delete audit logs (raises PermissionError)
- Even direct database edits are blocked by the model

**What gets logged:** performed_by, action (CREATE/UPDATE/DELETE/LOGIN/LOGOUT/DENIED), model_name, object_id, old_value, new_value, IP address, user agent, timestamp.

### 10.4 Security Headers (settings.py)

```python
SECURE_BROWSER_XSS_FILTER = True       # XSS protection
SECURE_CONTENT_TYPE_NOSNIFF = True     # MIME sniffing prevention
X_FRAME_OPTIONS = 'DENY'              # Clickjacking prevention
SESSION_COOKIE_HTTPONLY = True         # JS can't steal session cookie
SESSION_COOKIE_SAMESITE = 'Lax'       # CSRF protection
CSRF_COOKIE_HTTPONLY = True
```

---

## 11. External System Integration — Direct API

**For groups that ALREADY have their own login page.** Your login form sends credentials to our API, we return a JWT token.

### Step 1: Register a Client in Keycloak

1. Keycloak admin → govasset realm → Clients → Create client
2. Client ID: `your-app-name`
3. Client authentication: ON
4. Standard flow: ON
5. Direct access grants: ON
6. Save → Copy Client Secret from Credentials tab

### Step 2: Login Endpoint

```
POST https://YOUR-SERVER.up.railway.app/api/auth/login/
Content-Type: application/json

{
    "username": "moh_admin",
    "password": "Admin@123"
}
```

**Success (200):**
```json
{
    "access": "eyJhbGciOiJIUzI1NiIs...",
    "refresh": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
        "id": 29,
        "username": "moh_admin",
        "full_name": "Amina Hassan",
        "email": "amina@moh.go.tz",
        "role": "MINISTRY_ADMIN",
        "ministry_schema": "moh_schema"
    }
}
```

**Error (401 — wrong password):**
```json
{
    "error": true,
    "message": "Incorrect username or password. 2 attempts remaining before your account is locked.",
    "code": "authentication_required",
    "status": 401
}
```

**Error (429 — temp locked):**
```json
{
    "error": true,
    "message": "Too many failed attempts. Please wait 5 minutes before trying again.",
    "code": "temp_locked",
    "status": 429
}
```

**Error (403 — account disabled):**
```json
{
    "error": true,
    "message": "Your account has been disabled due to repeated failed login attempts.",
    "code": "account_disabled",
    "status": 403
}
```

### Step 3: Verify Token Endpoint

```
GET https://YOUR-SERVER.up.railway.app/api/auth/verify-token/
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

Returns: `{"valid": true, "user": {"id": 29, "username": "...", "role": "...", ...}}`

### Step 4: Refresh Token Endpoint

```
POST https://YOUR-SERVER.up.railway.app/api/auth/refresh/
Content-Type: application/json

{ "refresh": "eyJhbGciOiJIUzI1NiIs..." }
```

Returns new `access` + `refresh` tokens.

### External System Login Flow

```
User types username + password on YOUR login form
         ↓
Your backend calls POST /api/auth/login/
         ↓
Success → Save access + refresh tokens
         ↓
Call GET /api/auth/verify-token/ to get role + ministry
         ↓
Create a session in your system → redirect to your dashboard

On every page load:
  Call GET /api/auth/verify-token/ to validate the session
  If 401 → call POST /api/auth/refresh/
  If refresh fails too → redirect to your login page
```

---

## 12. External System Integration — SSO Redirect

**For groups that DON'T have a login page.** User clicks "Login with GovAsset" and gets redirected to Keycloak.

### Step 1: Redirect User to Keycloak

```
https://keycloak-production-4f96.up.railway.app/realms/govasset/protocol/openid-connect/auth
  ?client_id=group2-app
  &redirect_uri=https://their-system.com/auth/callback
  &response_type=code
  &scope=openid profile email
```

### Step 2: Handle the Callback

```python
# Exchange code for tokens:
POST https://keycloak-production-4f96.up.railway.app/realms/govasset/protocol/openid-connect/token

grant_type=authorization_code
&client_id=group2-app
&client_secret=their-secret
&code={code-from-url}
&redirect_uri=https://their-system.com/auth/callback
```

### Step 3: Get User Info

```
GET https://keycloak-production-4f96.up.railway.app/realms/govasset/protocol/openid-connect/userinfo
Authorization: Bearer {access_token}
```

---

## 13. Complete API Endpoint Reference

### Authentication

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| POST | `/api/auth/login/` | Log in, get JWT token | Anyone |
| POST | `/api/auth/refresh/` | Refresh expired token | Anyone with valid refresh |
| GET | `/api/auth/me/` | Get my profile | Logged in |
| GET | `/api/auth/verify-token/` | Verify token for external systems | Logged in |
| POST | `/api/auth/logout/` | Log out, blacklist token | Logged in |

### Assets

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/api/assets/` | List assets (with filters: search, status, category, condition) | Most roles |
| POST | `/api/assets/` | Create new asset (auto-generates number) | Non-auditors |
| GET | `/api/assets/{id}/` | Get single asset details | Most roles |
| PUT | `/api/assets/{id}/` | Update asset (field-level audit logging) | Non-auditors |
| DELETE | `/api/assets/{id}/` | Delete asset | Ministry Admin+ |
| GET | `/api/assets/categories/` | List asset categories | Most roles |

### Organisation

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/api/org-units/` | Get org hierarchy tree + flat facility list | Most roles |

### Audit

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/api/audit-logs/` | Paginated audit logs with action/model filters | Auditors+ |

### Dashboard

| Method | Endpoint | Purpose | Access |
|--------|----------|---------|--------|
| GET | `/api/dashboard/stats/` | Dashboard statistics (counts, expiry warnings) | Logged in |

---

## 14. Test Accounts

All use password: **`Admin@123`**

| Username | Role | Ministry | Schema |
|----------|------|----------|--------|
| `superadmin` | SUPER_ADMIN | All (central) | (none) |
| `moh_admin` | MINISTRY_ADMIN | Ministry of Health | `moh_schema` |
| `mnh_manager` | AGENCY_MANAGER | Ministry of Health | `moh_schema` |
| `rad_clerk` | FACILITY_CLERK | Ministry of Health | `moh_schema` |
| `moh_auditor` | AUDITOR | Ministry of Health | `moh_schema` |
| `mof_admin` | MINISTRY_ADMIN | Ministry of Finance | `mof_schema` |
