# External System — SSO Integration Guide

## How Your System Connects to the Government Asset Platform

---

## Contents

- [Overview — What This Guide Covers](#overview--what-this-guide-covers)
- [What We Each Do](#what-we-each-do)
- [What You Give Us (3 things)](#what-you-give-us-3-things)
- [What We Give You (4 things)](#what-we-give-you-4-things)
- [The 4-Step Setup](#the-4-step-setup)
- [How Login Works Step by Step](#how-login-works-step-by-step)
- [Your Callback Handler Code](#your-callback-handler-code)
- [All API Endpoints](#all-api-endpoints)
- [The 5 Roles Explained](#the-5-roles-explained)
- [Multi-Tenancy (Ministries)](#multi-tenancy-ministries)
- [Test Accounts](#test-accounts)
- [Logout](#logout)
- [Sample Code (Python)](#sample-code-python)
- [Common Problems](#common-problems)
- [Integration Checklist](#integration-checklist)
- [Summary](#summary)

---

## Overview — What This Guide Covers

This document is the **standard integration method** for any external government system that needs to connect to the Government Asset Platform. Whether you are a university project team, a ministry IT department, or a third-party developer — the process is the same.

**What you get by integrating:**
- Your users log in using a **single government-wide account** — no separate passwords for your system
- We handle all user management, role assignment, and password security
- You receive the user's identity, role, and ministry — you control what your UI shows or hides

**Two authentication methods (you choose):**

| Method | When to use | How it works |
|--------|------------|-------------|
| **Type A — SSO Redirect** | Your system has no login page. You redirect users to our Keycloak login page. | User clicks "Login with Government SSO" → goes to our Keycloak → comes back with their identity |
| **Type B — Direct API** | Your system has its own login page. You collect username + password yourself. | Your frontend sends credentials to `POST /api/auth/login/` → receives a token → your backend calls verify-token |

**Most external systems choose Type A (SSO Redirect)** because it is more secure — your system never handles passwords.

---

## What We Each Do

| We (Platform Team) handle | Your system handles |
|---|---|
| Login page (Keycloak SSO) | Your application screens and UI |
| All usernames and passwords | Showing/hiding buttons based on user role |
| User management (create/edit/delete users) | Displaying the user's name on your UI |
| Role management (5 roles — see below) | Filtering data by ministry |
| Ministry management (multi-tenancy) | Calling our API to verify users |
| Running Keycloak + API 24/7 on Railway | Making your callback URL publicly accessible |

**In one sentence:** Your users log in through our login page — we tell you who they are, what role they have, and which ministry they belong to. You just check the role and show/hide buttons.

---

## What You Give Us (3 things)

**Send these to us BEFORE we can set up your integration in our Keycloak server:**

| What we need | Example | Why |
|---|---|---|
| **Your application name** | e.g., `Group 2 Asset Registration System`, `Ministry of Health HR Portal`, `Treasury Audit Dashboard` | We label your app in our Keycloak admin console so we can identify it |
| **Your callback URL** | e.g., `https://group2-system.com/auth/callback`, `https://moh-portal.go.tz/oauth/callback` | Where we send users AFTER they successfully log in on our Keycloak page |
| **Your logout redirect URL** | e.g., `https://group2-system.com/logout`, `https://moh-portal.go.tz/bye` | Where we send users AFTER they log out, so they land back on your site |

**Important requirements for the callback URL:**
- It MUST be publicly accessible over the internet — we cannot redirect to `http://localhost`, `http://127.0.0.1`, or any private address
- The path `/auth/callback` is just an example — you can use any path your backend supports (/oauth/callback, /sso/return, etc.)
- It MUST use `https://` in production (most browsers block `http://` redirects with OIDC)
- The exact URL must match what we register in Keycloak — including trailing slash or no trailing slash

### Testing on your local machine (ngrok)

If your system is not yet deployed to the internet, use **ngrok** to create a temporary public URL:

```
1. Download ngrok from https://ngrok.com
2. Start your system on your local machine (e.g., port 3000)
3. In a terminal: ngrok http 3000
4. ngrok gives you a URL like: https://abc123.ngrok-free.app
5. Your callback URL becomes: https://abc123.ngrok-free.app/auth/callback
6. Send this URL to us
```

The ngrok URL changes every time you restart ngrok — so you will need to send us a new URL each time.

---

## What We Give You (4 things)

After you send us your application name and callback URL, we create an OIDC client in our Keycloak server and send you:

| What we give you | Example | Why you need it |
|---|---|---|
| **Client ID** | e.g., `group2-app`, `moh-hr-portal`, `treasury-audit` | Identifies YOUR application to our Keycloak server |
| **Client Secret** | e.g., `a1b2c3d4-e5f6-7890-abcd-ef1234567890` | Proves YOUR application is authorized to receive user data (keep this secret — never expose it in frontend/browser code!) |
| **Our Keycloak URL** | `https://keycloak-production-4f96.up.railway.app` | The authentication server — you redirect users here to log in |
| **Our Django API URL** | `https://goverment-assets-platform-production.up.railway.app` | The API server — you call this to verify user tokens and get identity |

Both URLs are **permanent** — they never change. Our services run 24/7 on Railway.

---

## The 4-Step Setup

Here is the entire integration at a glance:

```
Step 1: You add a "Login with Government SSO" button on your page
   ↓
Step 2: User clicks the button → redirected to our Keycloak → logs in with their government credentials
   ↓
Step 3: Keycloak sends the user BACK to your callback URL with a temporary authorization code
   ↓
Step 4: YOUR BACKEND exchanges the code for tokens → calls our API → receives the user's identity, role, and ministry
```

**That is it.** Your users never create passwords on your system. They use the government Keycloak — one account for all connected government services.

---

## How Login Works Step by Step

```
Browser Tab (Your Site)              Our Keycloak                    Your Backend
─────────────────────────            ───────────────                 ────────────────

1. User clicks "Login with
   Government SSO"
   → redirects to Keycloak ──────→  2. Shows login page
                                      3. User types username + password
                                      4. Verifies credentials with Keycloak
    5. Redirects back ←─────────────
    to YOUR callback URL
    with ?code=abc123&state=xyz

                                      6. Your server POSTs ─────────→
                                      our token endpoint
                                      with the code + client_secret

                                      ←────── 7. Returns tokens ────
                                      (access_token, id_token,
                                       refresh_token)

                                      8. Your server GETs ──────────→
                                      our verify-token API
                                      with the access_token

                                      ←── 9. Returns user info ─────
                                      { role, ministry, full_name,
                                        email, username }

10. You create a session in your app
    Show personalized dashboard:
    "Welcome, Amina Hassan"
    [Ministry of Health - Admin]
```

### How to Build the Login Button Link

When a user clicks your "Login with Government SSO" button, redirect their browser to this URL:

```
https://keycloak-production-4f96.up.railway.app/realms/govasset/protocol/openid-connect/auth?
    client_id=YOUR_CLIENT_ID&
    redirect_uri=https://YOUR_CALLBACK_URL&
    response_type=code&
    scope=openid+profile+email&
    state=YOUR_RANDOM_STRING
```

| Parameter | Value | Why |
|---|---|---|
| `client_id` | The Client ID we gave you (e.g., `group2-app`) | Identifies your app to our Keycloak |
| `redirect_uri` | Your callback URL (exact match) | Where to send the user back after login |
| `response_type` | `code` | Use the Authorization Code flow (most secure for web apps) |
| `scope` | `openid profile email` | Request the user's basic identity information |
| `state` | Random string you generate for each login | Security — prevents CSRF attacks |

**Important:** Generate a random `state` string for every login request. Store it in the user's session. When Keycloak sends the user back to your callback URL, verify that the `state` in the URL matches what you stored. If they do not match, REJECT the request — it is a CSRF attack.

---

## Your Callback Handler Code

When Keycloak sends the user back to your callback URL, your backend must handle the request in four steps:

### Step A — Verify the `state` parameter

```
Get: state  from the URL query parameters
Get: stored_state  from the user's session

if state != stored_state:
    REJECT — possible CSRF attack
else:
    CONTINUE
```

### Step B — Exchange the code for tokens

Your backend makes a **server-to-server** POST request. This MUST happen from your backend, not from the browser, because it includes your Client Secret.

```
POST https://keycloak-production-4f96.up.railway.app/realms/govasset/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=authorization_code
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&code=THE_CODE_FROM_THE_URL
&redirect_uri=https://YOUR_CALLBACK_URL
```

**Response (success):**
```json
{
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "expires_in": 300,
    "refresh_token": "eyJhbGciOiJIUzUxMiIs...",
    "id_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "Bearer"
}
```

Save the `access_token` for the next step. Save the `refresh_token` for when the access token expires (5 minutes). Save the `id_token` for logout.

### Step C — Call our verify-token API to get the user's identity

```
GET https://goverment-assets-platform-production.up.railway.app/api/auth/verify-token/
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Response (success):**
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

### Step D — Create a session and show your dashboard

Store the user information in your session. The user is now authenticated.

```python
# Pseudocode
session["user"] = {
    "id": response["user"]["id"],
    "username": response["user"]["username"],
    "full_name": response["user"]["full_name"],
    "role": response["user"]["role"],
    "ministry": response["user"]["ministry"]
}
session["access_token"] = access_token
session["refresh_token"] = refresh_token

# Show dashboard with user's name and role
render_dashboard(user=session["user"])
```

---

## All API Endpoints

### 1. Verify Token

**Purpose:** Check if a token is valid and get the user's full identity (role, ministry, name).

```
GET https://goverment-assets-platform-production.up.railway.app/api/auth/verify-token/
Headers:
  Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Success (200):**
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

**Error (401):**
```json
{
    "detail": "Given token not valid for any token type"
}
```

### 2. Refresh Token

**Purpose:** Get a new access token when the current one expires (access tokens are valid for 5 minutes).

```
POST https://keycloak-production-4f96.up.railway.app/realms/govasset/protocol/openid-connect/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&client_id=YOUR_CLIENT_ID
&client_secret=YOUR_CLIENT_SECRET
&refresh_token=YOUR_REFRESH_TOKEN
```

**Success (200):**
```json
{
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "expires_in": 300,
    "refresh_token": "eyJhbGciOiJIUzUxMiIs...",
    "token_type": "Bearer"
}
```

**If refresh fails (401):** The refresh token has also expired. Redirect the user back to the Keycloak login page to re-authenticate.

### 3. Direct Login (Type B — Alternative)

**Purpose:** Login directly with username and password. Use this ONLY if your system has its own login page and you cannot use the SSO redirect.

```
POST https://goverment-assets-platform-production.up.railway.app/api/auth/login/
Content-Type: application/json

{
    "username": "moh_admin",
    "password": "Admin@123"
}
```

**Success (200):**
```json
{
    "access": "eyJhbGciOiJSUzI1NiIs...",
    "refresh": "eyJhbGciOiJIUzUxMiIs...",
    "user": {
        "id": 29,
        "username": "moh_admin",
        "role": "MINISTRY_ADMIN",
        "ministry_schema": "moh_schema",
        "ministry": "Ministry of Health"
    }
}
```

**Error (401):**
```json
{
    "detail": "No active account found with the given credentials"
}
```

### 4. Get User Profile

**Purpose:** Get detailed profile information for the currently authenticated user.

```
GET https://goverment-assets-platform-production.up.railway.app/api/auth/profile/
Headers:
  Authorization: Bearer YOUR_ACCESS_TOKEN
```

**Response (200):**
```json
{
    "id": 29,
    "username": "moh_admin",
    "email": "amina@moh.go.tz",
    "full_name": "Amina Hassan",
    "role": "MINISTRY_ADMIN",
    "ministry_schema": "moh_schema",
    "ministry": "Ministry of Health",
    "is_active": true,
    "is_locked": false
}
```

---

## The 5 Roles Explained

Every user in the system is assigned exactly **one** of the following roles. Your application should check the `role` field from the verify-token response and adjust your UI accordingly.

| Role | Who has this role | What your UI should do |
|---|---|---|
| `SUPER_ADMIN` | Platform system administrators | Show ALL data across all ministries (include a ministry selector). Show ALL buttons (create, edit, delete). Full access. |
| `MINISTRY_ADMIN` | Ministry IT staff (one per ministry) | Show full access within their own ministry only. Show ALL buttons. Must NEVER see data from other ministries. |
| `AGENCY_MANAGER` | Agency directors, hospital managers | Show create + edit buttons. **Hide the delete button.** Limited to their agency's data within their ministry. |
| `FACILITY_CLERK` | Store clerks, frontline staff | Show create + edit on their own records. **Hide delete.** **Hide user management entirely.** |
| `AUDITOR` | Government auditors, inspectors | **Read-only access.** Hide ALL create, edit, and delete buttons. View data only. |

### How to Implement Role Checks in Your Code

```python
# Pseudocode — adapt to your programming language
role = user_data["user"]["role"]

if role == "SUPER_ADMIN":
    show_all_data()
    show_all_buttons()

elif role == "MINISTRY_ADMIN":
    show_data_for(user_data["user"]["ministry"])
    show_all_buttons()

elif role == "AGENCY_MANAGER":
    show_data_for(user_data["user"]["ministry"])
    show_create_and_edit_buttons()
    hide_delete_button()

elif role == "FACILITY_CLERK":
    show_own_records_only()
    show_create_and_edit_buttons()
    hide_delete_button()
    hide_user_management()

elif role == "AUDITOR":
    show_data_readonly()
    hide_all_modify_buttons()  # No create, edit, or delete
```

---

## Multi-Tenancy (Ministries)

The platform currently serves multiple government ministries. Each ministry's data is stored in a completely separate database schema. When a user logs in, they can only see data from their own ministry — even if there is a bug in your code, the database itself prevents cross-ministry access.

### Current Ministries

| Ministry | Internal Schema ID | Users in this ministry |
|---|---|---|
| **Ministry of Health** | `moh_schema` | moh_admin, mnh_manager, rad_clerk, moh_auditor |
| **Ministry of Finance** | `mof_schema` | mof_admin |

### What This Means for Your System

- When a user logs in, we return two ministry-related fields:
  - `ministry` — Human-readable name, e.g., `"Ministry of Health"` — display this on your UI
  - `ministry_schema` — Internal ID, e.g., `"moh_schema"` — use this for API calls that need to filter by ministry
- Your system should ONLY show data for the user's ministry
- A Ministry of Health user must NEVER see Ministry of Finance data, and vice versa
- If you are building a UI that lists or filters data, always include the `ministry` or `ministry_schema` as a filter

---

## Test Accounts

All test accounts use the password: `Admin@123`

| Username | Full Name | Role | Ministry |
|---|---|---|---|
| `superadmin` | System Administrator | SUPER_ADMIN | All ministries |
| `moh_admin` | Amina Hassan | MINISTRY_ADMIN | Ministry of Health |
| `mnh_manager` | John Mwangi | AGENCY_MANAGER | Ministry of Health |
| `rad_clerk` | Asha Salum | FACILITY_CLERK | Ministry of Health |
| `moh_auditor` | David Mushi | AUDITOR | Ministry of Health |
| `mof_admin` | Grace Mbwilo | MINISTRY_ADMIN | Ministry of Finance |

### Recommended Test Sequence

Test your integration by logging in as different users and verifying that your UI responds correctly:

```
TEST 1: Login as moh_admin
  → Expected: "Amina Hassan" + "MINISTRY_ADMIN" + "Ministry of Health"
  → All buttons visible (create, edit, delete)
  → See Ministry of Health data only, NOT Finance data

TEST 2: Login as rad_clerk
  → Expected: "Asha Salum" + "FACILITY_CLERK" + "Ministry of Health"
  → Delete button should be HIDDEN or DISABLED
  → Create and edit buttons should be VISIBLE

TEST 3: Login as moh_auditor
  → Expected: "David Mushi" + "AUDITOR" + "Ministry of Health"
  → ALL create/edit/delete buttons should be HIDDEN
  → Read-only view only

TEST 4: Login as mof_admin
  → Expected: "Grace Mbwilo" + "MINISTRY_ADMIN" + "Ministry of Finance"
  → See Ministry of Finance data only, NOT Health data
  → All buttons visible within their ministry

TEST 5: Login as superadmin
  → Expected: "System Administrator" + "SUPER_ADMIN" + no specific ministry
  → Should be able to access ALL ministries' data
  → All buttons visible
```

---

## Logout

When a user clicks "Logout" on your system, redirect their browser to our Keycloak logout endpoint:

```
https://keycloak-production-4f96.up.railway.app/realms/govasset/protocol/openid-connect/logout?
    id_token_hint=THE_ID_TOKEN_FROM_LOGIN&
    post_logout_redirect_uri=https://YOUR_LOGOUT_URL
```

| Parameter | Value | Why |
|---|---|---|
| `id_token_hint` | The `id_token` you received during login | Tells Keycloak which user session to end |
| `post_logout_redirect_uri` | Your logout redirect URL | Sends the user back to your site after logout completes |

This performs **single sign-out** — the user is logged out of the Government Asset Platform AND all other connected systems that use the same Keycloak session.

---

## Sample Code (Python)

This complete Python example shows the full integration flow. Adapt it to your programming language and framework.

```python
import requests
import secrets
from urllib.parse import urlencode

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION — Replace these with the values we give you
# ═══════════════════════════════════════════════════════════════

CLIENT_ID = "your-client-id"                    # We send you this
CLIENT_SECRET = "your-client-secret"            # We send you this (KEEP SECRET!)
KEYCLOAK_URL = "https://keycloak-production-4f96.up.railway.app"
API_URL = "https://goverment-assets-platform-production.up.railway.app"
CALLBACK_URL = "https://your-system.com/auth/callback"   # Your callback URL
LOGOUT_REDIRECT_URL = "https://your-system.com"          # Where users go after logout

# ═══════════════════════════════════════════════════════════════
# STEP 1: Generate the Login URL
# Put this code in the handler for your "Login with Government SSO" button
# ═══════════════════════════════════════════════════════════════

state = secrets.token_urlsafe(32)
# TODO: Store 'state' in the user's session for later verification

login_url = f"{KEYCLOAK_URL}/realms/govasset/protocol/openid-connect/auth?" + urlencode({
    "client_id": CLIENT_ID,
    "redirect_uri": CALLBACK_URL,
    "response_type": "code",
    "scope": "openid profile email",
    "state": state,
})

# Redirect the user's browser to: login_url
print(f"Redirect user to: {login_url}")


# ═══════════════════════════════════════════════════════════════
# STEP 2: Callback Handler
# This runs when Keycloak redirects the user back to your callback URL
# The URL will have ?code=xxx&state=yyy as query parameters
# ═══════════════════════════════════════════════════════════════

def handle_callback(request):
    """
    Called when Keycloak redirects the user back to your callback URL.
    Request contains 'code' and 'state' in the query parameters.
    """
    code = request.GET.get("code")
    state_from_url = request.GET.get("state")

    # 2a. Verify state matches what you stored earlier
    stored_state = session.get("oauth_state")  # Retrieve from session
    if state_from_url != stored_state:
        raise Exception("State mismatch — possible CSRF attack. Rejecting request.")

    # 2b. Exchange the authorization code for tokens
    token_response = requests.post(
        f"{KEYCLOAK_URL}/realms/govasset/protocol/openid-connect/token",
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": CALLBACK_URL,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_response.raise_for_status()
    tokens = token_response.json()

    access_token = tokens["access_token"]
    id_token = tokens["id_token"]
    refresh_token = tokens["refresh_token"]

    # 2c. Call our verify-token API to get the user's identity
    user_response = requests.get(
        f"{API_URL}/api/auth/verify-token/",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    user_response.raise_for_status()
    user_data = user_response.json()

    # 2d. Store user info in session
    session["user"] = user_data["user"]
    session["access_token"] = access_token
    session["refresh_token"] = refresh_token
    session["id_token"] = id_token

    # Now redirect to your dashboard
    # You can access:
    #   user_data["user"]["full_name"]    — "Amina Hassan"
    #   user_data["user"]["role"]          — "MINISTRY_ADMIN"
    #   user_data["user"]["ministry"]      — "Ministry of Health"
    return redirect("/dashboard")


# ═══════════════════════════════════════════════════════════════
# STEP 3: Refresh Token (call this before API calls)
# Access tokens expire after 5 minutes. Refresh before they expire.
# ═══════════════════════════════════════════════════════════════

def refresh_access_token():
    """Get a new access token using the refresh token."""
    refresh_response = requests.post(
        f"{KEYCLOAK_URL}/realms/govasset/protocol/openid-connect/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": session["refresh_token"],
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    if refresh_response.status_code != 200:
        # Refresh failed — redirect user to login again
        return redirect(login_url)

    new_tokens = refresh_response.json()
    session["access_token"] = new_tokens["access_token"]
    # Some implementations also return a new refresh token
    if "refresh_token" in new_tokens:
        session["refresh_token"] = new_tokens["refresh_token"]

    return session["access_token"]


# ═══════════════════════════════════════════════════════════════
# STEP 4: Logout URL (redirect user here when they click Logout)
# ═══════════════════════════════════════════════════════════════

def handle_logout(request):
    """Redirect the user to Keycloak to end their session."""
    logout_url = f"{KEYCLOAK_URL}/realms/govasset/protocol/openid-connect/logout?" + urlencode({
        "id_token_hint": session.get("id_token", ""),
        "post_logout_redirect_uri": LOGOUT_REDIRECT_URL,
    })

    # Clear your local session
    session.clear()

    # Redirect to Keycloak for global logout
    return redirect(logout_url)
```

---

## Common Problems

| Problem | Cause | Fix |
|---|---|---|
| `"Invalid redirect URI"` | The callback URL in your login link does not exactly match what we registered in Keycloak | Check for trailing slash mismatch (`/callback` vs `/callback/`). Check `http://` vs `https://`. |
| `"State mismatch"` error | You did not store the `state` parameter, or you are comparing it incorrectly | Generate a new random `state` for each login, store it in the user's session before redirecting, and verify it when the user returns |
| `verify-token` returns 401 | The access token has expired (tokens are valid for 5 minutes) | Use your saved `refresh_token` to get a new access token |
| Token refresh also returns 401 | The refresh token has also expired | Redirect the user back to the Keycloak login page to re-authenticate |
| `"User not found"` from verify-token | The user exists in Keycloak but has not been created in our Django database | Contact the platform team — we need to create the user in our system and assign them a role and ministry |
| Keycloak page shows "Could not find user" | The username does not exist | Double-check the username. If the user needs a new account, contact the platform team. |
| Keycloak login page will not load | Our server might be temporarily unreachable | Contact the platform team. Our services run 24/7 on Railway and are monitored. |
| Your callback handler returns an error | Bug in your implementation | Check your server logs. The most common issues are: (1) incorrect Client Secret, (2) wrong token endpoint URL, (3) the code exchange or verify-token call is failing |

---

## Integration Checklist

### Before starting, send us:

- [ ] **Your application name** — e.g., "Group 2 Asset Registration System", "Ministry of Health HR Portal"
- [ ] **Your callback URL** — must be publicly accessible and use `https://`
- [ ] **Your logout redirect URL** — where users return after logging out

### We will send you:

- [ ] **Client ID** — unique identifier for your application
- [ ] **Client Secret** — keep this secret, never expose it in browser code
- [ ] **Our Keycloak URL** — `https://keycloak-production-4f96.up.railway.app`
- [ ] **Our API URL** — `https://goverment-assets-platform-production.up.railway.app`

### Implement in your system:

- [ ] Host your callback URL so it is publicly accessible over the internet
- [ ] Add a "Login with Government SSO" button that links to our Keycloak authorization URL
- [ ] Generate a random `state` parameter for each login request and store it in the user's session
- [ ] Create a callback handler endpoint that processes the OIDC response
- [ ] Exchange the authorization code for tokens via POST to our token endpoint
- [ ] Call `GET /api/auth/verify-token/` with the access token to get the user's identity
- [ ] Use `user.role` to control permissions — hide/show buttons based on the role
- [ ] Use `user.ministry` to filter data — never show data from another ministry
- [ ] Implement token refresh — call the refresh endpoint before the 5-minute access token expires
- [ ] Handle the logout flow — redirect users to our Keycloak logout endpoint

---

## Summary

| Question | Answer |
|---|---|
| **Do I need to build a login page?** | No — your users log in on our Keycloak page (Type A). If you have your own login page, use Type B (Direct API). |
| **Do I store passwords?** | No — the platform handles all password storage and verification. |
| **Do I manage users?** | No — the platform creates and manages all users. You just display their name. |
| **Do I manage roles?** | No — you read the `role` field from our API response and adjust your UI accordingly. |
| **Do I manage ministries?** | No — you read the `ministry` field from our API response and filter data accordingly. |
| **Do I need to host my system publicly?** | Yes — your callback URL must be accessible from the internet so Keycloak can redirect users back to your system. |
| **What do I actually need to build?** | A "Login with Government SSO" button, a callback handler endpoint, role-based permission checks in your UI, and a logout handler. That is it. |
