# Direct API Integration Guide

## For Groups With Their Own Login Page

**From:** Group 1 — Administration, Security & Multi-tenancy
**To:** Groups 5, 6, etc. — groups that already have a login form

---

## When To Use This Guide

Use this guide if your group **already built your own login page** and you want users to log in on your site, not on ours. Your login form sends the credentials to our API, we verify them, and we return a JWT token.

If your group does NOT have a login page, use the **SSO Integration Guide** (`EXTERNAL_SSO_INTEGRATION.md`) instead — it's simpler (you don't need to build anything).

---

## What You Need (3 API Endpoints)

Your system only needs to call **3 endpoints** from our API:

| # | Endpoint | Purpose |
|---|----------|---------|
| 1 | `POST /api/auth/login/` | Send username + password → get JWT token |
| 2 | `GET /api/auth/verify-token/` | Get user's role, name, and ministry |
| 3 | `POST /api/auth/refresh/` | Get a new access token when it expires |

---

## Endpoint 1: Login

Your login form collects the username and password. Your backend sends them to our API:

```
POST https://YOUR_SERVER:8000/api/auth/login/
Content-Type: application/json

{
    "username": "moh_admin",
    "password": "Admin@123"
}
```

### Success — HTTP 200

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

Save `access` and `refresh` — you will use them below.

### Error — HTTP 401 (Wrong Password)

```json
{
    "error": true,
    "message": "Incorrect username or password. 2 attempts remaining before your account is locked.",
    "code": "authentication_required",
    "status": 401
}
```

Show this message on your login form. Let the user try again.

### Error — HTTP 429 (Too Many Attempts)

```json
{
    "error": true,
    "message": "Too many failed attempts. Please wait 5 minutes before trying again.",
    "code": "temp_locked",
    "status": 429
}
```

Tell the user to wait 5 minutes before trying again.

### Error — HTTP 403 (Account Locked)

```json
{
    "error": true,
    "message": "Your account has been disabled due to repeated failed login attempts. An unlock link has been sent to your registered email address.",
    "code": "account_disabled",
    "status": 403
}
```

Tell the user to check their email for an unlock link or contact their Ministry Administrator.

---

## Endpoint 2: Verify Token

After login, call this to get the user's full profile including role and ministry.

```
GET https://YOUR_SERVER:8000/api/auth/verify-token/
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Success — HTTP 200

```json
{
    "valid": true,
    "user": {
        "id": 29,
        "username": "moh_admin",
        "full_name": "Amina Hassan",
        "email": "amina@moh.go.tz",
        "role": "MINISTRY_ADMIN",
        "ministry_schema": "moh_schema",
        "ministry": "Ministry of Health"
    }
}
```

### Error — HTTP 401

```json
{
    "detail": "Given token not valid for any token type"
}
```

The token has expired. Call Endpoint 3 to refresh it.

---

## Endpoint 3: Refresh Token

When the access token expires (after 30 minutes), use the refresh token to get a new one:

```
POST https://YOUR_SERVER:8000/api/auth/refresh/
Content-Type: application/json

{
    "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

### Success — HTTP 200

```json
{
    "access": "eyJhbGciOiJIUzI1NiIs...",
    "refresh": "eyJhbGciOiJIUzI1NiIs..."
}
```

Use the new `access` token for subsequent API calls.

### Error — HTTP 401

```json
{
    "error": true,
    "message": "Token is invalid or expired...",
    "code": "authentication_required",
    "status": 401
}
```

The refresh token has also expired. Send the user back to your login form.

---

## Your Login Flow (Summary)

```
User types username + password on YOUR login form
         ↓
Your backend calls POST /api/auth/login/
         ↓
Success → Save access + refresh tokens
         ↓
Call GET /api/auth/verify-token/ to get role + ministry
         ↓
Create a session for the user in your system
         ↓
Redirect user to your dashboard

On every page load:
  Call GET /api/auth/verify-token/ to validate the session
  If 401 → call POST /api/auth/refresh/
  If refresh fails too → redirect to your login page
```

---

## The 5 Roles

| Role | Access Level |
|------|-------------|
| `SUPER_ADMIN` | Full access to everything |
| `MINISTRY_ADMIN` | Full access within their ministry |
| `AGENCY_MANAGER` | Agency-level access |
| `FACILITY_CLERK` | Can register and edit assets |
| `AUDITOR` | Read-only access |

Use `role` to control permissions, `ministry_schema` to scope data.

---

## Test Accounts (Password: `Admin@123`)

| Username | Role | Ministry |
|----------|------|----------|
| `superadmin` | SUPER_ADMIN | All |
| `moh_admin` | MINISTRY_ADMIN | Ministry of Health |
| `mnh_manager` | AGENCY_MANAGER | Ministry of Health |
| `rad_clerk` | FACILITY_CLERK | Ministry of Health |
| `moh_auditor` | AUDITOR | Ministry of Health |
| `mof_admin` | MINISTRY_ADMIN | Ministry of Finance |
