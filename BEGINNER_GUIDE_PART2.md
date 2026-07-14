# GOVERNMENT ASSET MANAGEMENT PLATFORM

# BEGINNER COMPLETE SYSTEM GUIDE — PART 2

## Chapters 7–14: Authentication, JWT, Login, Keycloak, Database, Requests, Security

---

> **Chapters:** [7](#ch-7) · [8](#ch-8) · [9](#ch-9) · [9B](#ch-9b) · [10](#ch-10) · [11](#ch-11) · [12](#ch-12) · [13](#ch-13) · [14](#ch-14) · [15](#ch-15)

---

<a name="ch-7"></a>
## CHAPTER 7: AUTHENTICATION

<a name="7-1"></a>
### 7.1 The Most Important Distinction

**Authentication** = "Are you who you say you are?" (Who are you?)
**Authorization** = "What are you allowed to do?" (What can you do?)

```
AUTHENTICATION
┌─────────────────────────────────────────────────────────────┐
│ You walk into a building. The security guard asks for ID.  │
│ You show your employee badge. The guard checks: is this    │
│ a real badge? Is it expired? Is it yours?                  │
│                                                             │
│ RESULT: "Yes, you are Amina Hassan. You may enter."         │
│         This is AUTHENTICATION.                             │
└─────────────────────────────────────────────────────────────┘

AUTHORIZATION
┌─────────────────────────────────────────────────────────────┐
│ Now you are inside. Can you enter the server room?          │
│ The guard checks: does Amina have server room access?       │
│                                                             │
│ RESULT: "Your badge is for Finance department only.         │
│         You cannot enter the server room."                  │
│         This is AUTHORIZATION.                              │
└─────────────────────────────────────────────────────────────┘
```

**In our project:**

```
Authentication:
  - Web: Keycloak checks username + password → "valid, this is who they say"
  - Mobile: Django checks username + password → "valid"

Authorization:
  - Web decorator: @role_required('MINISTRY_ADMIN') → "allowed or blocked"
  - API permission: CanManageAssets → "allowed to create/edit or read-only"
```

<a name="7-2"></a>
### 7.2 The Players in Authentication

| Term | What it means | In our project |
|------|---------------|----------------|
| **Identity** | Who a user is, uniquely | `username = "moh_admin"`, `id = 1` |
| **Credentials** | Proof of identity | Password, JWT token, Keycloak session |
| **Principal** | The currently authenticated user | `request.user` in Django |
| **Subject** | The user being acted upon | The user who is logging in |
| **Claims** | Facts about the user | role, ministry_schema, keycloak_id |
| **Token** | A signed package of claims | JWT access token |

<a name="7-3"></a>
### 7.3 Our Authentication Flow (Two Paths)

```
PATH 1: WEB BROWSER (Keycloak SSO)

Browser          Keycloak          Django          Database
  │                 │                │               │
  │──/login/───────→│                │               │
  │                 │──Login page────│               │
  │←─Login form────│                │               │
  │                 │                │               │
  │──username/pwd──→│                │               │
  │                 │  verify pwd    │               │
  │                 │  ✓ valid       │               │
  │                 │                │               │
  │←─Auth code─────│                │               │
  │                 │                │               │
  │──/oidc/callback/│                │               │
  │  with code──────┼───────────────→│               │
  │                 │                │──find user───→│
  │                 │                │←──found──────│
  │                 │                │  update user  │
  │                 │                │  create sess. │
  │                 │                │               │
  │←──Dashboard────┼────────────────│               │


PATH 2: MOBILE APP (Direct JWT)

Flutter           Django          Database
  │                 │               │
  │──/api/auth/     │               │
  │  login/         │               │
  │  username+pwd──→│               │
  │                 │──find user───→│
  │                 │←──found──────│
  │                 │  check pwd    │
  │                 │  check lockout│
  │                 │  create JWT   │
  │                 │  record audit │
  │                 │               │
  │←─JWT token─────│               │
  │                 │               │
  │──/api/assets/   │               │
  │  Bearer JWT────→│               │
  │                 │ verify JWT    │
  │                 │ switch schema │
  │                 │──query───────→│
  │                 │←──results────│
  │                 │               │
  │←─JSON assets───│               │
```

<a name="7-4"></a>
### 7.4 The Five Roles (Authorization)

Defined in `authentication/models.py`:

```python
ROLE_CHOICES = [
    ("SUPER_ADMIN",     "Super Admin"),       # Platform-wide access
    ("MINISTRY_ADMIN",  "Ministry Admin"),    # One ministry, full control
    ("AGENCY_MANAGER",  "Agency Manager"),    # Agency-level access
    ("FACILITY_CLERK",  "Facility Clerk"),    # One facility, basic ops
    ("AUDITOR",         "Auditor"),           # Read-only, all ministries
]
```

**What each role can do:**

| Action | SUPER_ADMIN | MINISTRY_ADMIN | AGENCY_MANAGER | FACILITY_CLERK | AUDITOR |
|--------|:-----------:|:--------------:|:--------------:|:--------------:|:-------:|
| View assets (own ministry) | ✓ (all) | ✓ | ✓ | ✓ | ✓ |
| Create assets | ✓ | ✓ | ✓ | ✓ | ✗ |
| Edit assets | ✓ | ✓ | ✓ | ✓ | ✗ |
| Delete assets | ✓ | ✓ | ✗ | ✗ | ✗ |
| Manage users | ✓ | ✓ | ✗ | ✗ | ✗ |
| Manage ministries | ✓ | ✗ | ✗ | ✗ | ✗ |
| View audit logs | ✓ | ✓ | ✗ | ✗ | ✓ |
| Org unit management | ✓ | ✓ | ✗ | ✗ | ✗ |

<a name="7-5"></a>
### 7.5 Where Roles Are Checked

**For web pages** — Decorators in `authentication/decorators.py`:

```python
@login_required_custom           # Must be logged in
@role_required('SUPER_ADMIN')    # Must be Super Admin specifically
def ministry_list_view(request):
    ...
```

```python
@login_required_custom
@ministry_isolation_check  # Must have a ministry schema (or be Super Admin)
def asset_list_view(request):
    ...
```

**For API endpoints** — Permission classes in `authentication/api_permissions.py`:

```python
class CanManageAssets(BasePermission):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True  # Anyone can read
        return request.user.role in [
            'SUPER_ADMIN', 'MINISTRY_ADMIN',
            'AGENCY_MANAGER', 'FACILITY_CLERK'
        ]
```

<a name="7-6"></a>
### 7.6 Schema Isolation (Database-Level Authorization)

File: `authentication/middleware.py`:

```python
class SchemaMiddleware:
    def process_request(self, request):
        if request.user.is_authenticated:
            request.schema_name = request.user.ministry_schema or 'public'
```

Then in views:
```python
def my_view(request):
    with schema_context(request.schema_name):
        # This query ONLY runs in that ministry's schema
        assets = Asset.objects.all()
```

**Result:** A user assigned to `moh_schema` literally CANNOT access `mof_schema` data — the database schema switch prevents it.

<a name="7-7"></a>
### 7.7 Panel Questions for Chapter 7

**Q: What is the difference between authentication and authorization?**
A: Authentication proves who you are (login). Authorization determines what you can do (permissions). Authentication happens first. Keycloak handles authentication for web users. Our decorators and permission classes handle authorization for both web and API users.

**Q: What are the five roles and what do they do?**
A: SUPER_ADMIN (manages the platform), MINISTRY_ADMIN (manages one ministry), AGENCY_MANAGER (manages an agency), FACILITY_CLERK (manages one facility), AUDITOR (read-only). Each role has progressively more restricted permissions.

**Q: How do you prevent a user from accessing another ministry's data?**
A: Two layers. First, roles and permissions control what the user can see at the application level. Second, database schema isolation ensures that even if a bug allows access, the query runs in the wrong schema and returns no data.

**Q: What is a claim?**
A: A piece of information about a user embedded in the token. Our JWT tokens contain claims like `role`, `ministry_schema`, `full_name`, and `email`. These travel with the token so the system always knows who the user is.

<a name="7-8"></a>
### 7.8 Beginner Misconceptions

**Misconception:** "Once I log in, I can see everything."
**Truth:** Logging in = authentication. What you see = authorization. Your role determines which pages work and which API calls succeed. A FACILITY_CLERK sees a different dashboard than a MINISTRY_ADMIN.

**Misconception:** "Roles are stored in Keycloak."
**Truth:** Roles are stored in Django's database (the `role` field on `CustomUser`). Keycloak stores the same role as an attribute. They are kept in sync.

**Misconception:** "Authentication and authorization are the same thing."
**Truth:** They are completely different. Authentication = proving identity (username + password). Authorization = checking permissions (role). Many beginners confuse them.

---

<a name="ch-8"></a>
## CHAPTER 8: JWT (JSON WEB TOKENS)

<a name="8-1"></a>
### 8.1 The Core Concept

**A JWT is a digital ID card that expires.**

Imagine a hotel key card:
- You check in → they give you a key card
- The key card opens your room for 3 days
- After 3 days, the card stops working
- If you lose it, the finder can only use it for 3 days
- You cannot change what's written on the card

**A JWT works exactly the same way:**
- You log in → the system gives you a JWT token
- The token proves your identity for 30 minutes
- After 30 minutes, the token stops working
- If someone steals it, they can only use it for 30 minutes

<a name="8-2"></a>
### 8.2 What a JWT Looks Like

A JWT is a long string in three parts, separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.
eyJ1c2VyX2lkIjoxLCJyb2xlIjoiTU9IX0FETUlOIn0.
abc123def456ghi789jkl012mno345pqr678stu901vwx
│                     │                             │
HEADER               PAYLOAD                      SIGNATURE
```

<a name="8-3"></a>
### 8.3 The Three Parts

**Part 1: HEADER** — Algorithm and token type
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Part 2: PAYLOAD** — The actual data
```json
{
  "token_type": "access",
  "exp": 1700000000,
  "iat": 1699998200,
  "user_id": 1,
  "role": "MINISTRY_ADMIN",
  "ministry_schema": "moh_schema",
  "full_name": "Amina Hassan"
}
```

**Part 3: SIGNATURE** — Mathematical proof the token is authentic

```
signature = HMAC-SHA256(
    base64(header) + "." + base64(payload),
    SECRET_KEY
)
```

<a name="8-4"></a>
### 8.4 How Verification Works

```
SERVER RECEIVES TOKEN:

1. Split token by "." → header, payload, signature
2. Decode header → get algorithm
3. Recompute signature:
   expected = HMAC-SHA256(header + "." + payload, SECRET_KEY)
4. Compare with received signature
5. If they match → token is VALID
6. If they don't match → token is TAMPERED → reject
7. Check expiration: if exp < now → EXPIRED → reject
```

**What happens if someone tampers:**

```
Attacker changes payload from FACILITY_CLERK to SUPER_ADMIN.
But the signature was computed for the ORIGINAL payload.
Server recomputes signature → doesn't match → REJECTED.

This is why JWT is secure. Payload and signature are
mathematically linked. You cannot change one without
breaking the other.
```

<a name="8-5"></a>
### 8.5 Access Tokens vs. Refresh Tokens

| | Access Token | Refresh Token |
|---|---|---|
| **Purpose** | Proves identity for API calls | Gets new access tokens |
| **Lifetime** | 30 minutes | 1 day |
| **Can access data?** | Yes | No |
| **Blacklisted?** | No | Yes |

**Why two tokens:**

```
Problem: If access token never expires, a stolen token works forever.
Solution: Access tokens last only 30 minutes.

Problem: User must log in every 30 minutes.
Solution: Refresh token (1 day) gets new access tokens silently.

Flow:
  1. Login → access (30 min) + refresh (1 day)
  2. After 25 min, Flutter refreshes silently
  3. Old refresh token is BLACKLISTED
  4. New access + new refresh issued
  5. User never notices
```

<a name="8-6"></a>
### 8.6 Where JWT Is Created

File: `authentication/api_serializers.py`, `CustomTokenObtainPairSerializer`:

```python
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom fields
        token['role'] = user.role
        token['ministry_schema'] = user.ministry_schema or ''
        token['full_name'] = user.get_full_name() or user.username
        token['email'] = user.email or ''
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'full_name': user.get_full_name() or user.username,
            'role': user.role,
            'ministry_schema': user.ministry_schema or '',
        }
        return data
```

<a name="8-7"></a>
### 8.7 Where Token Settings Are Configured

File: `config/settings.py`:

```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

<a name="8-8"></a>
### 8.8 Comparison: JWT vs. Sessions vs. Cookies

| Feature | JWT | Session | Cookie |
|---------|-----|---------|--------|
| Where is data stored? | In the token itself | On the server | In the browser |
| Server verification | Check signature | Look up session ID | Read cookie value |
| Scalable? | Yes (no server storage) | No | Yes |
| Revocable? | No (until expiry) | Yes (delete session) | No |
| Used for? | Mobile apps, APIs | Web browsers | Preferences |

<a name="8-9"></a>
### 8.9 Panel Questions for Chapter 8

**Q: What is JWT and why do we use it?**
A: JWT is a digital ID card that proves a user's identity. It contains user information (role, ministry) with a cryptographic signature preventing tampering. It is stateless — the server does not store session data, making it scalable and ideal for mobile apps.

**Q: What is the difference between an access token and a refresh token?**
A: An access token is short-lived (30 min) and used to access data. A refresh token is long-lived (1 day) and only used to get new access tokens. This limits damage if an access token is stolen while providing good user experience.

**Q: How does JWT prevent tampering?**
A: The signature is cryptographically created from the header + payload + secret key. Anyone changing the payload breaks the signature. The server recalculates the expected signature on every request and rejects mismatches.

**Q: Can a JWT be revoked?**
A: Not directly. Once issued, it is valid until expiry. We mitigate with short lifetimes (30 min) and blacklisting refresh tokens. For emergency revocation, we could change the SECRET_KEY (invalidating all tokens).

<a name="8-10"></a>
### 8.10 Beginner Misconceptions

**Misconception:** "JWT is encrypted and nobody can read it."
**Truth:** JWT is SIGNED, not encrypted. The header and payload are Base64-encoded (not encrypted). Anyone can decode and read them. The signature just prevents tampering. Never put secrets (like passwords) in a JWT.

**Misconception:** "The refresh token can access data like the access token."
**Truth:** No. The refresh token can ONLY get new access tokens. It cannot call `/api/assets/` or any data endpoint. It has a single purpose: to exchange for new access tokens.

**Misconception:** "If I log out, my JWT is destroyed."
**Truth:** The access token remains valid until it expires (even after logout). Only the refresh token is blacklisted. The access token will work until its 30-minute expiry. This is why access tokens are short-lived.

---

<a name="ch-9"></a>
## CHAPTER 9: LOGIN

<a name="9-1"></a>
### 9.1 The Three Login Paths

```
PATH 1: Web Browser via Keycloak SSO
User goes to http://localhost:8000/login/
Clicks "Sign in with Government SSO"
Types password into Keycloak's page
Sees dashboard with session cookie

PATH 2: Mobile App via Direct API
User opens Flutter app
Types username + password into the app
Receives JWT token, sees asset list

PATH 3: External Government System via API
System calls POST /api/auth/login/ programmatically
Receives JWT token, calls other endpoints
```

<a name="9-2"></a>
### 9.2 Path 1: Web Browser Login (Complete Trace)

```
STEP 1: User visits http://localhost:8000/
STEP 2: Django checks: is this user logged in?
        ↓ No session → redirect to /login/
STEP 3: User sees login page with "Sign in with Government SSO" button
        File: templates/authentication/login.html
STEP 4: User clicks the button
        ↓ Django redirects browser to Keycloak:
        https://localhost:8180/realms/govasset/protocol/openid-connect/auth?
          response_type=code&
          client_id=govasset-django&
          redirect_uri=http://localhost:8000/oidc/callback/&
          scope=openid+profile+email&
          prompt=login
STEP 5: Browser shows Keycloak's login page
        User types: moh_admin / Admin@123
STEP 6: Keycloak verifies password → correct
        ↓ Creates temporary authorization code
STEP 7: Keycloak redirects browser back to Django:
        http://localhost:8000/oidc/callback/?code=abc123
STEP 8: Django sends code back to Keycloak (server-to-server):
        POST https://localhost:8180/realms/govasset/protocol/openid-connect/token
          client_id=govasset-django
          client_secret=...
          code=abc123
          grant_type=authorization_code
STEP 9: Keycloak returns: access_token + id_token
STEP 10: Django's OIDC backend runs:
         File: authentication/oidc_backend.py
         filter_users_by_claims(claims) → finds user by keycloak_id
         update_user(user, claims) → updates role and ministry
STEP 11: Django creates a session (session cookie in browser)
STEP 12: Browser redirects to /dashboard/
         dashboard_view() runs → shows MOH statistics
```

<a name="9-3"></a>
### 9.3 What Happens If No Django User Exists

```
STEPS 1-9: Same as above (Keycloak validates password)

STEP 10: Django's OIDC backend:
         filter_users_by_claims(claims)
         ↓ Not found by keycloak_id or username
         Returns empty queryset

STEP 10b: create_user(claims) is called
          ↓ BLOCKED — we DON'T auto-create users
          ↓ Instead, create PendingAccess record
          ↓ Set session flag: pending_access_notice = True
          ↓ Return None (login blocked)

STEP 11: Browser redirected to /login/?error=auth_failed
         Shows message:
         "Your account is not yet registered in our system."

STEP 12: Super Admin goes to /pending-access/
         Sees the pending request
         Reviews and either APPROVES or REJECTS
```

<a name="9-4"></a>
### 9.4 Path 2: Mobile App Login (Complete Trace)

```
STEP 1: User opens Flutter app, types credentials, taps Login
STEP 2: Flutter sends POST http://192.168.100.18:8000/api/auth/login/
        Body: {"username": "moh_admin", "password": "Admin@123"}
STEP 3: Django receives at LoginAPIView (file: authentication/api_views.py)
STEP 4: _is_locked_out("moh_admin", "192.168.100.50")
        ↓ Check LoginAttempt table
        ↓ If locked → return 429 with minutes remaining
STEP 5: Validate credentials via CustomTokenObtainPairSerializer
STEP 6: If INVALID password:
        _record_failed_attempt() → increment counter
        If attempts >= 5 → set locked_until = now + 15 min
        Return 401 with remaining attempts count
STEP 7: If VALID password:
        _clear_failed_attempts() → reset counter
        Generate JWT tokens with custom claims
        Record LOGIN in audit log
STEP 8: Django returns:
        {
          "access": "eyJ...",
          "refresh": "eyJ...",
          "user": {"id": 1, "username": "moh_admin", "role": "MINISTRY_ADMIN", ...}
        }
STEP 9: Flutter stores token, navigates to asset list
```

<a name="9-5"></a>
### 9.5 The Audit Trail on Login

Every login is recorded in TWO places:

**1. Database — AuditLog table:**
```python
AuditLog.objects.create(
    performed_by_id=user.id,
    performed_by_name="Amina Hassan",
    action='LOGIN',
    model_name='CustomUser',
    object_id='1',
    ip_address='192.168.100.50',
    user_agent='Flutter/3.22 (dart:io)',
)
```

**2. Log file — logs/security.log:**
```
INFO 2025-06-27 09:30:00 authentication: API Login success: moh_admin from 192.168.100.50
WARNING 2025-06-27 09:31:00 authentication: API Login blocked (locked): hacker from 10.0.0.99
```

<a name="9-6"></a>
### 9.6 Panel Questions for Chapter 9

**Q: How does the web login work?**
A: The web uses Keycloak SSO. The user is redirected to Keycloak's login page, types their password into Keycloak (not our system). Keycloak verifies and redirects back to Django. Django exchanges the code for user info, finds or creates the local user, and starts a session.

**Q: How does the mobile login work?**
A: The mobile app sends username and password directly to our API. Django's LoginAPIView validates credentials, checks brute-force lockout, generates JWT tokens, and returns them.

**Q: Why doesn't the mobile app use Keycloak?**
A: Keycloak requires redirecting to a web browser, which is clunky on a phone. Mobile uses direct API login for a smoother experience. Both methods end with the same JWT token.

**Q: Where is the login recorded?**
A: Two places: the AuditLog database table (permanent, tamper-proof) and the security.log file (real-time monitoring). Failed attempts are in the LoginAttempt table.

<a name="9-7"></a>
### 9.7 Beginner Misconceptions

**Misconception:** "The web login and mobile login are the same."
**Truth:** They are completely different flows. Web uses Keycloak SSO (redirect to Keycloak page). Mobile uses direct API (username/password sent to Django). The result is the same — a logged-in session — but the path is different.

**Misconception:** "Logout destroys my JWT token."
**Truth:** The access token remains valid until it expires (30 min). Logout only blacklists the refresh token. The access token can still be used until it expires naturally.

**Misconception:** "If I close the app, I'm logged out."
**Truth:** The Flutter app stores the refresh token securely. When you reopen the app, it can silently get a new access token. You stay logged in until the refresh token expires (1 day) or you explicitly log out.

---

<a name="ch-9b"></a>
## CHAPTER 9B: HOW THE SERVER REMEMBERS YOU (OIDC + AUTH METHODS)

<a name="9b-1"></a>
### 9B.1 What Is OIDC?

**OIDC (OpenID Connect)** is the protocol our Keycloak SSO uses. It is a standard way for one system (Django) to trust another system (Keycloak) for login.

You see "oidc" everywhere in our project because it is how the web login works:

- `/oidc/authenticate/` — Starts the login process (sends you to Keycloak)
- `/oidc/callback/` — Where Keycloak sends you back after login
- `authentication/oidc_backend.py` — The Django code that handles the OIDC flow
- `mozilla_django_oidc` — The Django package that implements OIDC
- `OIDC_*` settings in `config/settings.py` — All the OIDC configuration

**Without OIDC:**
```
Django: "Type your password here" → Django checks it
Problem: Django stores your password. If hacked, passwords leak.
```

**With OIDC:**
```
Django: "Go to Keycloak to log in"
Browser goes to Keycloak, types password
Keycloak verifies password ✓
Keycloak gives browser a ONE-TIME CODE
Browser brings code back to Django
Django calls Keycloak (server-to-server): "Is this code valid?"
Keycloak: "Yes, this is Amina Hassan, role=MINISTRY_ADMIN"
Django: "Welcome, Amina!" (creates session)

Key point: Django NEVER sees the password. The code is one-time-use.
```

**OIDC flow step by step (Authorization Code Flow):**

```
BROWSER                     KEYCLOAK                    DJANGO
   │                          │                           │
   │  1. Click "SSO Login"    │                           │
   │──────────────────────────┼──────────────────────────→│
   │                          │                           │
   │  2. "Go log in at        │                           │
   │     Keycloak"            │                           │
   │←─────────────────────────┼───────────────────────────│
   │                          │                           │
   │  3. Types password       │                           │
   │─────────────────────────→│                           │
   │                          │ 4. Verifies ✓             │
   │                          │ 5. Creates one-time code  │
   │                          │                           │
   │  6. Redirects with code  │                           │
   │←─────────────────────────│                           │
   │                          │                           │
   │  7. Sends code to Django │                           │
   │──────────────────────────┼──────────────────────────→│
   │                          │                           │
   │                          │  8. Django sends code     │
   │                          │     + client_secret       │
   │                          │     to Keycloak           │
   │                          │←─────────────────────────→│
   │                          │                           │
   │                          │  9. "Code valid! Here's   │
   │                          │     user info"            │
   │                          │                           │
   │ 10. Django creates       │                           │
   │     session, shows       │                           │
   │     dashboard            │                           │
   │←─────────────────────────┼───────────────────────────│
```

**Why OIDC is secure:**
- The code is one-time-use (if stolen, cannot be reused)
- The client_secret proves Django is really our app
- The password is only typed into Keycloak's page (not our server)
- Django and Keycloak talk server-to-server (no browser can intercept)

<a name="9b-2"></a>
### 9B.2 The Four Ways a Server Can Remember You

There are four main methods. We use TWO of them:

| Method | Where we use it | How it works | Analogy |
|--------|----------------|--------------|---------|
| **Session cookie** | Web browser login | Server stores your info in a database table. Gives your browser a cookie with a random ID. On every request, browser sends the cookie. Server looks up the ID in the database. | A coat check ticket — you give your coat to the attendant, they give you a ticket. You bring the ticket back to get your coat. |
| **JWT (JSON Web Token)** | Mobile app / API | Server creates a signed token containing your user info. No database lookup needed — the token itself proves who you are. App stores it and sends it on every request. Server verifies the signature. | A passport — it contains your photo and info, it's stamped by the government, and border agents verify the stamp. No phone call needed. |

**We do NOT use these two:**

| Method | Why we don't use it | How it would work |
|--------|---------------------|-------------------|
| **API Keys** | For machine-to-machine, not individual users | A static secret string given to a program. Never expires. Used by services like Google Maps. Our service accounts use username+password (like API keys but temporary). |
| **OAuth tokens** | OIDC *is* OAuth tokens — OIDC is built on top of OAuth 2.0 | OAuth is the parent protocol. OIDC is a layer on top that adds identity (who the user is, not just what they can access). |

<a name="9b-3"></a>
### 9B.3 Session Cookies Explained (How the Web Remembers You)

```
AFTER WEB LOGIN (via Keycloak):

1. Django creates a session record in the database:
   ┌──────────┬──────────────┬───────────┐
   │ session  │  user_id     │  expires  │
   │ key      │              │           │
   ├──────────┼──────────────┼───────────┤
   │ abc123   │  1           │  2 hrs    │
   └──────────┴──────────────┴───────────┘

2. Django sends a cookie to the browser:
   Set-Cookie: sessionid=abc123; expires=...

3. Browser stores the cookie.

4. On EVERY request, browser sends:
   Cookie: sessionid=abc123

5. Django looks up the session in the database:
   SELECT * FROM django_session WHERE session_key = 'abc123'
   → Finds user_id = 1
   → Sets request.user = CustomUser(id=1)

6. The session expires:
   - After 2 hours of inactivity (SESSION_COOKIE_AGE = 7200 seconds)
   - When the browser is closed (SESSION_EXPIRE_AT_BROWSER_CLOSE = True)
```

**Why sessions are secure:**
- The cookie is just a random ID. It doesn't contain user data.
- If the cookie is stolen, the attacker can only use it for 2 hours.
- Sessions can be revoked instantly (delete the session record).
- The session is stored on the server, so users cannot modify it.

<a name="9b-4"></a>
### 9B.4 JWT Explained (How the Mobile App Remembers You)

```
AFTER MOBILE LOGIN (via API):

1. Django creates a JWT token:
   Header: {"alg": "HS256", "typ": "JWT"}
   Payload: {"user_id": 1, "role": "MINISTRY_ADMIN", "exp": 1700000000}
   Signature: HMAC(header + "." + payload, SECRET_KEY)

2. Django returns the token:
   {
     "access": "eyJhbGciOiJIUzI1NiIs...",
     "refresh": "eyJhbGciOiJIUzI1NiIs..."
   }

3. Flutter stores it in secure storage (keychain on iOS, keystore on Android).

4. On EVERY request, Flutter sends:
   Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

5. Django decodes the token:
   - Verifies the signature (proves it wasn't tampered with)
   - Checks the expiration (exp) — if expired, reject
   - Reads user_id, role, ministry_schema from the payload
   - Sets request.user = CustomUser(id=1)

6. The token expires:
   - Access token: 30 minutes
   - Refresh token: 1 day
```

**Why JWT is secure (differently):**
- The token is SIGNED — cannot be tampered with.
- Short expiry (30 min) limits damage if stolen.
- No database lookup needed (faster, scalable).
- But cannot be revoked until it expires.

<a name="9b-5"></a>
### 9B.5 Session vs. JWT — The Trade-offs

| Feature | Session (Web) | JWT (Mobile/API) |
|---------|---------------|-------------------|
| **Where is data stored?** | Server database | Inside the token itself |
| **Server verification** | Look up session ID in DB | Verify cryptographic signature |
| **Can be revoked?** | Yes (delete session) | No (wait for expiry) |
| **How to log someone out instantly?** | Delete their session | You can't — token works until expiry |
| **Scalable?** | Needs shared session storage across servers | No server storage needed (fully stateless) |
| **Performance** | Database query on every request | Just signature verification (fast) |
| **Used by** | Web browser users | Mobile app, external systems |

**Both are important.** Web sessions give us instant revocation (an admin can lock out a user immediately). JWT gives us scalability and works well for mobile apps that may not have constant connectivity.

<a name="9b-6"></a>
### 9B.6 Panel Questions for Chapter 9B

**Q: What is OIDC and why do we use it?**
A: OIDC (OpenID Connect) is a standard protocol for Single Sign-On. It lets Django trust Keycloak for authentication. The user logs into Keycloak (not Django), and Keycloak gives Django a signed confirmation. This means Django never handles passwords. OIDC is the reason you see "oidc" everywhere — in URLs like /oidc/authenticate/, in the oidc_backend.py file, and in OIDC_* settings.

**Q: What is the difference between a session and a JWT?**
A: A session stores data on the server (the browser just has a cookie with an ID). A JWT stores data inside the token itself (the server verifies the signature). Sessions can be revoked instantly. JWTs cannot be revoked — they must expire. We use sessions for web (because we want instant revocation for admin actions) and JWTs for mobile (because they scale better and work offline).

**Q: Does the mobile app use sessions?**
A: No. The mobile app uses JWT tokens exclusively. There is no session cookie. The token is sent on every request. When it expires (30 min), the refresh token gets a new one.

**Q: Does the web browser use JWT?**
A: Not for normal browsing. The web uses session cookies. However, if the web browser calls the API (like from JavaScript), it would need to get a JWT separately.

**Q: What would happen if we used API Keys for users instead of JWT?**
A: API Keys are static and never expire. If stolen, they work forever. They are suitable for machine accounts (like a service account for another ministry), not for human users who need temporary access and revocation.

**Q: What is the relationship between OAuth 2.0 and OIDC?**
A: OAuth 2.0 is about authorization — "what can this app access?" OIDC is built on top of OAuth 2.0 and adds identity — "who is this user?" OIDC is OAuth 2.0 with an extra layer specifically for logging people in.

<a name="9b-7"></a>
### 9B.7 Beginner Misconceptions

**Misconception:** "OIDC and OAuth are the same thing."
**Truth:** OAuth is about ACCESS ("let this app read my data"). OIDC is about IDENTITY ("this is who I am"). OIDC uses OAuth as its foundation but adds the concept of "who the user is."

**Misconception:** "Sessions are outdated, JWT is better."
**Truth:** Both have different strengths. Sessions are better when you need instant revocation (lock out a fired employee immediately). JWT is better for scalability and mobile apps. We use BOTH — sessions for web, JWT for mobile.

**Misconception:** "The 'oidc' in URLs is a typo of 'oauth'."
**Truth:** OIDC stands for OpenID Connect. It is a different (but related) standard from OAuth. The URLs are correct.

**Misconception:** "Session cookies contain my user data."
**Truth:** Session cookies contain only a RANDOM ID. Your actual user data (name, role, etc.) is stored on the server in the session record. The cookie just points to it.

---

<a name="ch-10"></a>
## CHAPTER 10: KEYCLOAK

<a name="10-1"></a>
### 10.1 The Core Concept

**Keycloak is a separate program that handles passwords so our code doesn't have to.**

```
WITHOUT KEYCLOAK:
┌─────────────────────────────────────────────────────┐
│                   DJANGO                             │
│  Login form → Check password → Create session        │
│                                                      │
│  PROBLEMS:                                           │
│  1. We must STORE passwords (huge security risk)     │
│  2. We must hash passwords correctly                 │
│  3. A breach of our server leaks ALL passwords       │
│  4. Every system has its own password                │
└─────────────────────────────────────────────────────┘

WITH KEYCLOAK:
┌──────────────────────┐  ┌─────────────────────────────┐
│      DJANGO          │  │        KEYCLOAK              │
│  User visits login   │  │  User types password HERE    │
│  page                │  │  Keycloak checks password    │
│  ↓                   │  │  Keycloak stores password    │
│  Redirect to         │  │  Keycloak handles lockouts   │
│  Keycloak            │  │                              │
│  ↓                   │  │  Django NEVER sees the       │
│  Keycloak says "OK"  │  │  password at all             │
└──────────────────────┘  └─────────────────────────────┘
```

<a name="10-2"></a>
### 10.2 Why Governments Use SSO

**SSO = One password, many systems.**

```
WITHOUT SSO:
- Asset management system → login1
- HR system → login2
- Email → login3
- Budget system → login4
Total: 5 passwords to remember. People write them on sticky notes.

WITH SSO:
- One login → works everywhere
Total: 1 password to remember.
```

<a name="10-3"></a>
### 10.3 Keycloak Concepts

| Concept | What it is | In our project |
|---------|------------|----------------|
| **Realm** | A security domain | `govasset` — our realm |
| **Client** | A system using Keycloak | `govasset-django` — our Django app |
| **Client Secret** | Password for our app to talk to Keycloak | `i9bDUIzrXNATomD5IAtxuowZDmsHKqfb` |
| **User** | A person who can log in | Created in both Keycloak and Django |
| **Authorization Code** | Temporary one-time code | Used in OIDC flow |

<a name="10-4"></a>
### 10.4 Our Keycloak Configuration

From `.env`:
```
KEYCLOAK_SERVER_URL=http://localhost:8180
KEYCLOAK_REALM=govasset
KEYCLOAK_CLIENT_ID=govasset-django
KEYCLOAK_CLIENT_SECRET=i9bDUIzrXNATomD5IAtxuowZDmsHKqfb
KEYCLOAK_ADMIN_USERNAME=admin
KEYCLOAK_ADMIN_PASSWORD=Admin@123
```

From `config/settings.py`:
```python
OIDC_OP_AUTHORIZATION_ENDPOINT = "http://localhost:8180/realms/govasset/protocol/openid-connect/auth"
OIDC_OP_TOKEN_ENDPOINT = "http://localhost:8180/realms/govasset/protocol/openid-connect/token"
OIDC_OP_LOGOUT_ENDPOINT = "http://localhost:8180/realms/govasset/protocol/openid-connect/logout"
OIDC_RP_CLIENT_ID = "govasset-django"
OIDC_RP_CLIENT_SECRET = "..."
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_USE_PKCE = True
```

<a name="10-5"></a>
### 10.5 The OIDC Authorization Code Flow

```
1. Browser → /oidc/authenticate/ → Django
2. Django redirects browser to Keycloak login
   URL includes: client_id, redirect_uri, response_type=code
3. User logs into Keycloak
   Keycloak creates temporary authorization code
4. Keycloak redirects browser back to Django
   URL includes: ?code=abc123
5. Django exchanges code with Keycloak (server-to-server):
   POST /realms/govasset/protocol/openid-connect/token
     client_id, client_secret, code, grant_type=authorization_code
6. Keycloak returns access_token + id_token
7. Django reads user info from tokens
8. Django finds or creates local user
9. Django creates session, redirects to dashboard
```

<a name="10-6"></a>
### 10.6 Keycloak Admin API — Automatic User Management

File: `authentication/keycloak_admin.py`

```python
class KeycloakAdminService:
    def create_user(self, username, email, first_name, last_name, password, role, ministry_schema):
        # Login to Keycloak as admin
        token = self._get_admin_token()
        
        # Create the user
        response = requests.post(
            f"{self.server_url}/admin/realms/{self.realm}/users",
            headers={'Authorization': f'Bearer {token}'},
            json={
                'username': username,
                'email': email,
                'enabled': True,
                'attributes': {'role': [role], 'ministry_schema': [ministry_schema]},
            }
        )
        
        # Get UUID from Location header
        keycloak_id = response.headers['Location'].split('/')[-1]
        
        # Set password
        requests.put(
            f"{self.server_url}/admin/realms/{self.realm}/users/{keycloak_id}/reset-password",
            headers={'Authorization': f'Bearer {token}'},
            json={'type': 'password', 'value': password, 'temporary': False}
        )
        
        return keycloak_id
```

<a name="10-7"></a>
### 10.7 Our Custom OIDC Backend

File: `authentication/oidc_backend.py`

```python
class GovAssetOIDCBackend(OIDCAuthenticationBackend):
    def filter_users_by_claims(self, claims):
        # Called when user comes back from Keycloak
        # Try to find existing Django user by keycloak_id
        # If not found, try by username
        # If found by username but keycloak_id missing, link them
        
    def create_user(self, claims):
        # Called when no user found
        # Instead of auto-creating, create PendingAccess
        # Return None (login blocked)
        
    def update_user(self, user, claims):
        # Called when user found
        # Update their role and ministry_schema from Keycloak
```

<a name="10-8"></a>
### 10.8 Panel Questions for Chapter 10

**Q: Why use Keycloak instead of Django's built-in authentication?**
A: Django has a login system, but using it means we store passwords. If our server is breached, passwords are exposed. Keycloak is a purpose-built authentication server. By delegating to Keycloak, we never handle passwords directly.

**Q: What is SSO and why does the government need it?**
A: Single Sign-On means one password works across many systems. Without it, a government worker needs separate passwords for asset management, HR, email, budgeting — five passwords to remember. With SSO, one login works everywhere.

**Q: What is the OIDC authorization code flow?**
A: A secure protocol where: (1) User redirected from Django to Keycloak, (2) User logs into Keycloak, (3) Keycloak sends user back with a temporary code, (4) Django exchanges code for user info with Keycloak (server-to-server, not visible to browser). Password is only typed into Keycloak.

**Q: What is a client secret?**
A: A password identifying our Django app to Keycloak. When Django talks to Keycloak, it sends the client secret to prove it is really our application. Prevents other apps from pretending to be us.

<a name="10-9"></a>
### 10.9 Beginner Misconceptions

**Misconception:** "Keycloak is complicated and unnecessary."
**Truth:** Keycloak adds initial complexity but removes the burden of securely storing passwords. Password storage is easy to get wrong. Keycloak is used by governments worldwide and handles security correctly.

**Misconception:** "Keycloak replaces Django's user model."
**Truth:** Keycloak handles authentication (checking passwords). Django still stores user profiles (roles, ministry assignments) in its own database. Keycloak and Django work together — Keycloak verifies identity, Django stores permissions.

**Misconception:** "The mobile app uses Keycloak too."
**Truth:** No. Only the web browser uses Keycloak. The mobile app sends credentials directly to Django's API. This is a design choice — avoiding browser redirects on a phone.

---

<a name="10-10"></a>
### 10.10 The Honest Trade-off: Keycloak vs Simple Login

**Question:** "Why not just use one simple normal login for everyone, and put other groups in the sidebar?"

Could we remove Keycloak entirely, use a simple Django username-and-password login for the web too (exactly like mobile already does), and let other groups' systems simply be links in a sidebar?

**Could we?** Yes, technically. But a simple login solves a different, smaller problem than what Keycloak solves. A simple login proves "this password is correct *for this one system*." Keycloak proves "this password is correct, and *every other connected system can trust that too, without asking again*." That second thing — one password working across many separately built systems — is the real value of SSO (Single Sign-On).

**The honest trade-off:**

| Using Keycloak (what we did) | Using one simple shared login instead |
|---|---|
| One password really does work across many different systems built by different people | Each separately-built system still needs its own password, unless they all share one database directly |
| Built on a tested, internationally trusted tool, not our own homemade security code | We would be inventing our own mini version of Keycloak ourselves, with more risk of mistakes |
| Easy to defend: "we used an industry standard, not something we wrote ourselves" | Harder to defend: "we wrote our own central login system" sounds riskier to a security-focused examiner |

**The honest summary:** We could have used one simple shared login for everything, but that would mean quietly rebuilding our own version of Keycloak by hand. Using Keycloak directly gives us the same single-login benefit using a proven, tested, industry-standard tool instead of homemade security code.

---

<a name="ch-11"></a>
## CHAPTER 11: DATABASE

<a name="11-1"></a>
### 11.1 The Core Concept

**A database is a program that stores data persistently and lets you search it efficiently.**

Think of a database as a giant, perfectly organized filing cabinet:
- **Tables** = filing drawers (Users, Assets, AuditLogs)
- **Rows** = individual files in each drawer (one user per row)
- **Columns** = the fields on each file (username, password, role)

<a name="11-2"></a>
### 11.2 PostgreSQL vs. a Spreadsheet

| Feature | Excel | PostgreSQL |
|---------|-------|------------|
| Capacity | ~1 million rows | Billions of rows |
| Multiple users | One at a time | Hundreds simultaneously |
| Search speed | Slow with large data | Milliseconds (with indexes) |
| Data integrity | Type anything | Enforces rules (e.g., role must be one of 5 values) |
| Relationships | VLOOKUP (error-prone) | Foreign keys (enforced) |
| Backup | Copy the file | pg_dump (consistent, while running) |

<a name="11-3"></a>
### 11.3 Our Database Structure

**Database:** `government_assets_db`

```
government_assets_db
│
├── Schema: public (SHARED)
│   ├── authentication_customuser        → ALL user accounts
│   ├── authentication_pendingaccess     → Blocked login requests
│   ├── authentication_loginattempt      → Failed login tracking
│   ├── tenants_ministry                 → Ministry records
│   └── tenants_domain                   → URL-to-ministry mapping
│
├── Schema: moh_schema (MOH ONLY)
│   ├── assets_assetcategory             → MOH's categories
│   ├── assets_asset                     → MOH's assets
│   ├── organizations_orgunit            → MOH's org hierarchy
│   └── organizations_auditlog           → MOH's audit trail
│
└── Schema: mof_schema (MOF ONLY)
    ├── assets_assetcategory             → MOF's categories
    ├── assets_asset                     → MOF's assets
    └── ...
```

<a name="11-4"></a>
### 11.4 Key Tables

**authentication_customuser:**
| Column | Type | Example |
|--------|------|---------|
| id | Integer | 1 |
| username | Text | `moh_admin` |
| role | Text | `MINISTRY_ADMIN` |
| ministry_schema | Text | `moh_schema` |

**assets_asset:**
| Column | Type | Example |
|--------|------|---------|
| id | Integer | 42 |
| asset_number | Text (unique) | `MOH-ICT-2025-0001` |
| name | Text | `Dell Latitude 5440` |
| status | Text | `ACTIVE` |
| acquisition_cost | Decimal | 2850000.00 |

**organizations_auditlog:**
| Column | Type | Example |
|--------|------|---------|
| action | Text | `CREATE` |
| old_value | JSON | null |
| new_value | JSON | `{"name": "Dell Laptop"}` |
| timestamp | DateTime | 2025-06-27 09:30 |

<a name="11-5"></a>
### 11.5 How django-tenants Creates Schemas

```python
# In tenants/views.py:
ministry = Ministry(
    schema_name='moh_schema',
    name='Ministry of Health',
)
ministry.save()  # ← THE MAGIC LINE
```

When `.save()` is called, `django-tenants`:
1. Runs: `CREATE SCHEMA moh_schema;`
2. Creates all TENANT_APPS tables inside `moh_schema`
3. Creates the domain record for URL routing
4. Creates the root OrgUnit

<a name="11-6"></a>
### 11.6 How Schema Switching Works

File: `authentication/middleware.py`
```python
class SchemaMiddleware:
    def process_request(self, request):
        if request.user.is_authenticated:
            request.schema_name = request.user.ministry_schema or 'public'
```

Then in views:
```python
with schema_context(request.schema_name):
    assets = Asset.objects.all()
    # This runs: SELECT * FROM moh_schema.assets_asset
```

<a name="11-7"></a>
### 11.7 Foreign Keys

A foreign key connects one table to another:

```
assets_asset                     assets_assetcategory
┌──────────┬──────────────┐     ┌──────────┬──────────────────┐
│ id       │ category_id  │────→│ id       │ name             │
├──────────┼──────────────┤     ├──────────┼──────────────────┤
│ 1        │ 10           │     │ 10       │ ICT Equipment    │
│ 2        │ 10           │     │ 20       │ Vehicles         │
│ 3        │ 20           │     └──────────┴──────────────────┘
└──────────┴──────────────┘
```

In code:
```python
asset = Asset.objects.get(id=1)
print(asset.category.name)  # "ICT Equipment"
```

<a name="11-8"></a>
### 11.8 Panel Questions for Chapter 11

**Q: What database do you use and why?**
A: PostgreSQL. It is free, reliable, and supports schemas — which lets us split the database into separate sections for each ministry. MySQL cannot do this.

**Q: How do you keep ministries' data separate?**
A: Through PostgreSQL schemas. Each ministry gets its own schema. Django switches to the correct schema based on the logged-in user. Even a code bug cannot expose another ministry's data at the database level.

**Q: What is a foreign key?**
A: A connection between two tables. Every Asset has a `category_id` pointing to an AssetCategory. The database enforces that the category must exist.

**Q: What is a migration?**
A: A recorded change to the database structure. When we add a field to a model, Django generates a migration file with SQL commands. Migrations are stored in the `migrations/` folders and keep everyone's database in sync.

**Q: Why is the audit log immutable?**
A: AuditLog overrides save() and delete() to prevent modifications. Trying to edit or delete an existing entry raises PermissionError. This makes it legally defensible.

---

<a name="ch-12"></a>
## CHAPTER 12: REQUEST LIFECYCLE

<a name="12-1"></a>
### 12.1 Complete Journey of One Request

Let's trace what happens when Flutter calls GET /api/assets/:

```
Flutter builds HTTP request:
  GET http://192.168.100.18:8000/api/assets/
  Authorization: Bearer eyJhbGci...

Phone sends over WiFi hotspot → laptop port 8000
```

<a name="12-2"></a>
### 12.2 Step 1: Django Receives

Django's development server receives raw bytes, parses HTTP:
- Method: GET
- Path: /api/assets/
- Headers: Authorization, User-Agent, Accept

<a name="12-3"></a>
### 12.3 Step 2: Middleware (11 layers)

```
1. TenantMainMiddleware    → Sets up database connection
2. SecurityMiddleware      → Security headers
3. SessionMiddleware       → Reads session cookie
4. CorsMiddleware          → CORS headers
5. CommonMiddleware        → URL normalization
6. CsrfViewMiddleware      → CSRF check (skipped for API)
7. AuthenticationMiddleware → Decodes JWT, sets request.user
8. MessagesMiddleware      → Message framework
9. XFrameOptionsMiddleware → Clickjacking protection
10. SchemaMiddleware (OUR) → Sets request.schema_name
11. SessionRefresh         → OIDC session check
```

<a name="12-4"></a>
### 12.4 Steps 3-8: View Processing

```
3. URL routing: /api/ → api_urls.py → assets/ → AssetListCreateAPIView
4. Permission checks: IsAuthenticated ✅, CanManageAssets ✅
5. View runs: AssetListCreateAPIView.get()
6. Database query: SELECT * FROM moh_schema.assets_asset WHERE status='ACTIVE'
7. Serialization: Asset objects → JSON via AssetSerializer
8. Response: HTTP 200 with JSON body

Total time: ~30 milliseconds
```

<a name="12-5"></a>
### 12.5 Timeline Diagram

```
Flutter              Network              Django              PostgreSQL
  │                     │                   │                    │
  │──GET /api/assets/──→│                   │                    │
  │  Bearer token       │──HTTP request────→│                    │
  │                     │              [Middleware × 11]        │
  │                     │              [URL routing]            │
  │                     │              [Permissions]            │
  │                     │              [View runs]              │
  │                     │                   │──SELECT * FROM───→│
  │                     │                   │  moh_schema.      │
  │                     │                   │  assets_asset     │
  │                     │                   │←──9 rows──────────│
  │                     │              [Serialize to JSON]      │
  │                     │←──HTTP 200 JSON───│                   │
  │←──Parse JSON───────│                                       │
  │  Display list       │                                       │
  │←── TOTAL: ~30ms ──→│                                       │
```

---

<a name="ch-13"></a>
## CHAPTER 13: COMPLETE REQUEST TRACE (PRODUCTION)

<a name="13-1"></a>
### 13.1 Production Architecture

In production, more layers are added:

```
INTERNET (users from anywhere)
    │
    ▼
NGINX (reverse proxy)
  - Serves static files directly
  - Terminates HTTPS
  - Load balancing across workers
  - Rate limiting
    │
    ▼
GUNICORN (WSGI server)
  - Runs multiple Django workers
  - Each worker handles one request at a time
    │
    ▼
DJANGO (same code as development)
  - DEBUG=False
  - ALLOWED_HOSTS locked down
    │
    ▼
POSTGRESQL (same database)
```

<a name="13-2"></a>
### 13.2 Dev vs. Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Server | `manage.py runserver` | Gunicorn + Nginx |
| HTTPS | No | Yes (SSL certificate) |
| Static files | Django serves them | Nginx serves directly |
| Concurrency | Single process | Multiple workers |
| Error display | Full traceback | Generic 500 page |
| Security | Relaxed (DEBUG=True) | Strict (DEBUG=False) |

---

<a name="ch-14"></a>
## CHAPTER 14: SECURITY

<a name="14-1"></a>
### 14.1 Our 9 Security Layers

```
LAYER 1 — HTTPS/TLS (in production)
  Protects: Eavesdropping, man-in-the-middle
  Encrypts ALL traffic between client and server

LAYER 2 — Multi-Tenant Schema Isolation
  Protects: Cross-ministry data breach
  Each ministry's data in its own PostgreSQL schema

LAYER 3 — Role-Based Access Control (RBAC)
  Protects: Unauthorized actions
  5 roles with different permissions

LAYER 4 — JWT Token Security
  Protects: Token theft, replay attacks
  30-min expiry, rotation, blacklisting

LAYER 5 — Keycloak SSO
  Protects: Password theft (we never store passwords)
  Authentication delegated to specialized system

LAYER 6 — Brute-Force Protection
  Protects: Password guessing
  5 attempts → 15 minute lockout

LAYER 7 — Immutable Audit Log
  Protects: Covering tracks
  No one can edit or delete audit entries

LAYER 8 — Pending Access Approval
  Protects: Unauthorized account creation
  No auto-creation — every account must be approved

LAYER 9 — Security Headers + Logging
  Protects: XSS, clickjacking, MIME sniffing
  Dual logging (database + file)
```

<a name="14-2"></a>
### 14.2 Layer 6: Brute-Force Protection

File: `authentication/models.py`

```python
class LoginAttempt(models.Model):
    MAX_ATTEMPTS = 5
    LOCKOUT_MINUTES = 15
    username = models.CharField(max_length=150)
    ip_address = models.GenericIPAddressField()
    attempts = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    
    @property
    def is_locked(self):
        if self.locked_until:
            return timezone.now() < self.locked_until
        return False
```

File: `authentication/api_views.py` (in `LoginAPIView`):

```python
def _is_locked_out(self, username, ip_address):
    try:
        attempt = LoginAttempt.objects.get(username=username, ip_address=ip_address)
        if attempt.locked_until and timezone.now() < attempt.locked_until:
            return True, attempt.minutes_remaining
    except LoginAttempt.DoesNotExist:
        pass
    return False, 0

def _record_failed_attempt(self, username, ip_address):
    attempt, _ = LoginAttempt.objects.get_or_create(
        username=username, ip_address=ip_address,
        defaults={'attempts': 0}
    )
    attempt.attempts += 1
    if attempt.attempts >= LoginAttempt.MAX_ATTEMPTS:
        attempt.locked_until = timezone.now() + timedelta(minutes=LoginAttempt.LOCKOUT_MINUTES)
    attempt.save()
    return attempt
```

<a name="14-3"></a>
### 14.3 Layer 7: Immutable Audit Log

File: `organizations/models.py`:

```python
class AuditLog(models.Model):
    def save(self, *args, **kwargs):
        if self.pk is not None:  # Record ALREADY exists
            raise PermissionError("AuditLog cannot be modified!")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("AuditLog cannot be deleted!")
```

You can CREATE an audit entry, but NEVER edit or delete an existing one.

<a name="14-4"></a>
### 14.4 Security Headers

File: `config/settings.py`:

```python
SECURE_CONTENT_TYPE_NOSNIFF = True      # Prevents MIME-type sniffing
SECURE_BROWSER_XSS_FILTER = True        # Enables browser XSS filter
X_FRAME_OPTIONS = 'DENY'               # Prevents clickjacking
CSRF_COOKIE_SECURE = True               # CSRF token only over HTTPS
SESSION_COOKIE_SECURE = True            # Session cookie only over HTTPS
SECURE_HSTS_SECONDS = 0                 # HSTS (set to 1 year in production)
```

<a name="14-5"></a>
### 14.5 Dual Logging

File: `config/settings.py`:

```python
LOGGING = {
    'loggers': {
        'authentication': {
            'handlers': ['security_file', 'console'],
            'level': 'INFO',
        },
    },
}
```

- `logs/django.log` — General errors and warnings
- `logs/security.log` — Login attempts, blocked access

<a name="14-6"></a>
### 14.6 Panel Questions for Chapter 14

**Q: What security features does your system have?**
A: Nine security measures: (1) Keycloak SSO — passwords never handled by us, (2) Role-based access — 5 roles control permissions, (3) Brute-force lockout — 5 wrong attempts lock for 15 min, (4) Immutable audit log — no editing or deleting, (5) JWT token security — 30-min expiry, rotation, blacklisting, (6) Pending access approval — no auto-created accounts, (7) Dual logging — database + file, (8) Security headers — XSS, clickjacking protection, (9) Schema isolation — database-level ministry separation.

**Q: How does brute-force protection work?**
A: Every failed login increments a counter per username+IP. After 5 failures, the account locks for 15 minutes (locked_until = now + 15 min). Successful login resets the counter. Locked users get HTTP 429 with minutes remaining.

**Q: Why is the audit log immutable?**
A: The save() method raises PermissionError if the record already exists. The delete() method always raises PermissionError. This makes audit entries legally admissible as evidence — nobody can cover their tracks.

**Q: How do you protect against SQL injection?**
A: Django's ORM automatically parameterizes queries. We never write raw SQL. User input is passed as parameters, not concatenated into SQL strings. This prevents SQL injection by design.

<a name="14-7"></a>
### 14.7 Beginner Misconceptions

**Misconception:** "JWT encryption makes the token secure."
**Truth:** JWT is SIGNED, not encrypted. Anyone can decode and read the payload. The signature only prevents tampering. Do not put secrets (passwords, API keys) in a JWT.

**Misconception:** "The security log is the same as the audit log."
**Truth:** The security log is a text file (logs/security.log) for real-time monitoring. The audit log is a database table (organizations_auditlog) for permanent, tamper-proof records. They serve different purposes.

**Misconception:** "If I'm an admin, I can delete audit entries."
**Truth:** The database model itself prevents deletion of audit entries. Even the Super Admin cannot delete an audit log. The admin could truncate the table via raw SQL, but that would require database administrator access, which is a separate role.

---

<a name="ch-15"></a>
## CHAPTER 15: DEPLOYING TO PRODUCTION / THE CLOUD

<a name="15-1"></a>
### 15.1 Development vs Production — The Two Worlds

```
DEVELOPMENT                              PRODUCTION
(Your Laptop)                            (Cloud Server)

┌────────────────────┐                  ┌──────────────────────┐
│ python manage.py   │                  │ Nginx (web server)   │
│ runserver          │                  │   └── reverse proxy  │
│ (Django dev server)│                  │       ┌──────────┐  │
│                    │                  │       │ Gunicorn │  │
│ SQLite or local    │                  │       │ (Django) │  │
│ PostgreSQL         │                  │       └──────────┘  │
│                    │                  │                      │
│ Keycloak: kc.bat   │                  │ Keycloak (cloud)     │
│ start-dev          │                  │                      │
│                    │                  │ PostgreSQL (managed) │
│ Hotspot WiFi       │                  │ HTTPS (TLS cert)     │
│ http://192.168.x.x │                  │ https://govasset.go  │
└────────────────────┘                  └──────────────────────┘

KEY DIFFERENCES:
┌────────────────────────────┬──────────────────────────────────┐
│ Development                │ Production                       │
├────────────────────────────┼──────────────────────────────────┤
│ Django runserver (single)  │ Gunicorn + Nginx (multi-worker)  │
│ HTTP (no encryption)       │ HTTPS (TLS certificate)          │
│ Hotspot / localhost        │ Public IP + real domain name     │
│ SECRET_KEY visible in code │ SECRET_KEY in environment var    │
│ DEBUG=True                 │ DEBUG=False                      │
│ SQLite or dev PostgreSQL   │ Managed PostgreSQL (RDS, etc.)   │
│ Manual restart             │ Auto-restart on crash            │
└────────────────────────────┴──────────────────────────────────┘
```

<a name="15-2"></a>
### 15.2 Production Architecture — What Replaces What

```
BEFORE (Development):
  Browser → Django runserver (port 8000) → SQLite/PostgreSQL

AFTER (Production):
  Browser → HTTPS → Nginx (port 443) → Gunicorn (port 8000) → PostgreSQL
                    Nginx (port 80)   → redirects to 443

WHAT EACH PIECE DOES:

Nginx (pronounced "engine-x")
  Replaces: Nothing — it's NEW in production
  Job: Reverse proxy, SSL termination, static files, rate limiting
  Think: The front desk receptionist who directs all visitors

Gunicorn (pronounced "gunicorn")
  Replaces: python manage.py runserver
  Job: Runs Django code with multiple workers (handles many requests at once)
  Think: Multiple waiters instead of one

PostgreSQL (managed, e.g., AWS RDS, DigitalOcean Managed DB)
  Replaces: Your local PostgreSQL
  Job: Same thing, but managed by a cloud provider (backups, updates, scaling)

Redis (optional but recommended)
  Replaces: Nothing — it's NEW
  Job: Cache, session storage, rate limiting counters
  Think: A fast notepad that sits next to the waiter
```

<a name="15-3"></a>
### 15.3 Choosing a Cloud Provider

| Provider | Cost (Monthly Est.) | Difficulty | Best For |
|----------|-------------------|------------|----------|
| **DigitalOcean App Platform** | ~$15-30/month | Easy | Beginners, Django-specific hosting |
| **PythonAnywhere** | ~$12/month | Easiest | Learning, small deployments |
| **AWS (EC2 + RDS)** | ~$30-80/month | Hard | Enterprise, full control |
| **Azure** | ~$30-80/month | Hard | Government contracts (Azure preferred) |
| **Linode** | ~$15-30/month | Medium | Good balance of cost and control |

**For a government project, consider these factors:**
- Data sovereignty: Must the data stay in Tanzania? Choose a provider with African regions (AWS Cape Town, Azure South Africa)
- Compliance: Does the provider meet government security standards?
- Support: Can you get timely support during business hours?

**Recommendation:** Start with DigitalOcean or Linode for simplicity and cost. Migrate to AWS/Azure if government compliance requires it.

<a name="15-4"></a>
### 15.4 Step-by-Step: Deploying on a VPS (Any Provider)

**Step 1: Provision a Server**

```bash
# You'll get root SSH access to a server with:
# - Ubuntu 22.04 LTS
# - 2 GB RAM (minimum for Django + PostgreSQL + Keycloak)
# - 50 GB SSD
# - Public IP: e.g., 159.89.100.50
```

**Step 2: Set Up the Server — One-Time Setup**

```bash
# SSH into your server
ssh root@159.89.100.50

# Update everything
apt update && apt upgrade -y

# Install Python, PostgreSQL, Nginx, Redis
apt install -y python3.10 python3.10-venv python3-pip
apt install -y postgresql postgresql-contrib
apt install -y nginx
apt install -y redis-server
```

**Step 3: Set Up PostgreSQL**

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database
CREATE DATABASE govasset;
CREATE USER govasset_user WITH PASSWORD 'Str0ng!DB#P@ss';
GRANT ALL PRIVILEGES ON DATABASE govasset TO govasset_user;
GRANT ALL PRIVILEGES ON SCHEMA public TO govasset_user;
ALTER DATABASE govasset OWNER TO govasset_user;

# Exit psql
\q
```

**Step 4: Clone and Configure the Project**

```bash
# Create a non-root user for the app
adduser --disabled-password govapp
usermod -aG sudo govapp
su - govapp

# Clone the project
git clone https://github.com/your-org/govasset-platform.git
cd govasset-platform

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# Create .env file (NEVER commit this to git!)
cat > .env << EOF
SECRET_KEY=generate-a-new-long-random-key-here
DEBUG=False
DB_NAME=govasset
DB_USER=govasset_user
DB_PASSWORD=Str0ng!DB#P@ss
DB_HOST=localhost
DB_PORT=5432
ALLOWED_HOSTS=.govasset.go.tz,159.89.100.50
KEYCLOAK_SERVER_URL=https://keycloak.govasset.go.tz
EOF
```

**Step 5: Configure Django Settings for Production**

File: `config/settings.py` (changes needed):

```python
# Production settings
DEBUG = os.getenv('DEBUG', 'False') == 'True'
SECRET_KEY = os.getenv('SECRET_KEY')
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '').split(',')

# Database (production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT'),
    }
}

# Security settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
```

**Step 6: Configure Nginx**

File: `/etc/nginx/sites-available/govasset`

```nginx
server {
    listen 80;
    server_name govasset.go.tz api.govasset.go.tz;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name govasset.go.tz api.govasset.go.tz;

    ssl_certificate /etc/letsencrypt/live/govasset.go.tz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/govasset.go.tz/privkey.pem;

    # Static files (Django's collected static)
    location /static/ {
        alias /home/govapp/govasset-platform/staticfiles/;
    }

    # Media files (uploaded images, documents)
    location /media/ {
        alias /home/govapp/govasset-platform/media/;
    }

    # API and everything else → Django
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Step 7: Set Up Gunicorn as a System Service**

File: `/etc/systemd/system/gunicorn.service`

```
[Unit]
Description=GovAsset Gunicorn service
After=network.target

[Service]
User=govapp
Group=www-data
WorkingDirectory=/home/govapp/govasset-platform
EnvironmentFile=/home/govapp/govasset-platform/.env
ExecStart=/home/govapp/govasset-platform/venv/bin/gunicorn \
    --workers 3 \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/gunicorn/access.log \
    --error-logfile /var/log/gunicorn/error.log \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
# Start and enable the service
sudo systemctl start gunicorn
sudo systemctl enable gunicorn
sudo systemctl status gunicorn
```

**Step 8: Set Up HTTPS with Let's Encrypt**

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx

# Get SSL certificate
certbot --nginx -d govasset.go.tz -d api.govasset.go.tz

# Certificates auto-renew. Test renewal:
certbot renew --dry-run
```

**Step 9: Set Up Keycloak in Production**

Keycloak should run on a separate server or use an external identity provider.

```bash
# Option A: Keycloak on same server (not recommended for production)
# Use Docker:
docker run -d \
  --name keycloak \
  -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=Strong!Admin#Pass \
  -e KC_DB=postgres \
  -e KC_DB_URL=jdbc:postgresql://localhost:5432/keycloak \
  -e KC_DB_USERNAME=keycloak_user \
  -e KC_DB_PASSWORD=Str0ng!DB#P@ss \
  quay.io/keycloak/keycloak:22.0.5 start

# Option B: Use Keycloak SaaS (e.g., Cloud-IAM, or managed Keycloak)
# This is the recommended approach for government projects.
```

**Step 10: Run Migrations and Collect Static Files**

```bash
cd /home/govapp/govasset-platform
source venv/bin/activate

# Run database migrations
python manage.py migrate_schemas --shared
python manage.py migrate

# Collect static files for Nginx to serve
python manage.py collectstatic --noinput

# Create super admin
python manage.py createsuperuser
```

**Final step:** Visit `https://govasset.go.tz` in your browser.

<a name="15-5"></a>
### 15.5 Domain and DNS Setup

**For production, you need real domains:**

```
Your domains:
  govasset.go.tz          → Main website (public + all ministries via subdomain)
  moh.govasset.go.tz      → Ministry of Health portal
  mof.govasset.go.tz      → Ministry of Finance portal
  api.govasset.go.tz      → API endpoint
  keycloak.govasset.go.tz → Keycloak login page
  admin.govasset.go.tz    → Django admin (restrict access)

DNS records (set at your domain registrar):
  govasset.go.tz     A   → 159.89.100.50
  *.govasset.go.tz   A   → 159.89.100.50
                             (wildcard catches all subdomains)

Or use CNAME if you prefer:
  *.govasset.go.tz   CNAME → govasset.go.tz
```

**Register these domains in django-tenants:**

```python
# In production, create domains pointing to real URLs:
from tenants.models import Domain, Ministry

moh = Ministry.objects.get(schema_name='moh_schema')
Domain.objects.create(
    domain='moh.govasset.go.tz',
    tenant=moh,
    is_primary=True
)

mof = Ministry.objects.get(schema_name='mof_schema')
Domain.objects.create(
    domain='mof.govasset.go.tz',
    tenant=mof,
    is_primary=True
)

# API endpoint (routes to public schema, user determines schema)
api_tenant = Ministry.objects.get(schema_name='public')
Domain.objects.create(
    domain='api.govasset.go.tz',
    tenant=api_tenant,
    is_primary=True
)
```

<a name="15-6"></a>
### 15.6 Configuring django-tenants for Production

In `config/settings.py`:

```python
# Development mode (your laptop)
# SHOW_PUBLIC_IF_NO_TENANT_FOUND = True  ← allows IP access

# Production mode (real domains)
SHOW_PUBLIC_IF_NO_TENANT_FOUND = False
# Now every request MUST match a domain. Unknown domains get 404.

# If some external systems still access by IP:
# Create a domain entry for the server's IP:
Domain.objects.create(
    domain='159.89.100.50',       # ← your server's IP
    tenant=public_tenant,
    is_primary=False
)
```

<a name="15-7"></a>
### 15.7 Environment Variables and Secrets Management

**NEVER hardcode secrets. Always use environment variables or a secrets manager.**

```
.env file (stored on server, NOT in git):
──────────────────────────────────────
SECRET_KEY=django-insecure-abc123...  ← Generate with: python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
DEBUG=False
DB_PASSWORD=Str0ng!DB#P@ss
KEYCLOAK_CLIENT_SECRET=abc123...
EMAIL_HOST_PASSWORD=email_pass_here

For AWS: Use AWS Secrets Manager
For Azure: Use Azure Key Vault
For others: Use .env with restricted file permissions (chmod 600)
```

**Generate a SECRET_KEY:**
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

<a name="15-8"></a>
### 15.8 Setting Up django-tenants on a Fresh Database

When deploying to a fresh production database:

```bash
# 1. Run shared migrations (public schema)
python manage.py migrate_schemas --shared

# 2. Create the public tenant
python manage.py shell
```

```python
# In Django shell:
from django_tenants.utils import schema_context
from tenants.models import Ministry, Domain

# Create public tenant
public_tenant = Ministry(
    schema_name='public',
    name='Government Asset Platform',
    paid_until='2026-12-31',
    on_trial=False
)
public_tenant.save()

# Create domain for public tenant
Domain.objects.create(
    domain='govasset.go.tz',
    tenant=public_tenant,
    is_primary=True
)
Domain.objects.create(
    domain='api.govasset.go.tz',
    tenant=public_tenant,
    is_primary=False
)

# Create initial ministry (demo)
from schema_context import create_tenant
moh = create_tenant(
    name='Ministry of Health',
    schema_name='moh_schema',
    domain='moh.govasset.go.tz'
)
```

```bash
# 3. Now run tenant migrations
python manage.py migrate_schemas --executor=parallel
```

<a name="15-9"></a>
### 15.9 Backup Strategy

```
WHAT TO BACKUP:
┌──────────────────────┬──────────────┬────────────────────────────┐
│ What                 │ Frequency    │ How                         │
├──────────────────────┼──────────────┼────────────────────────────┤
│ PostgreSQL database  │ Daily        │ pg_dump → encrypted cloud   │
│ Media uploads        │ Daily        │ rsync or S3 sync            │
│ .env file            │ On change    │ Password manager + backup   │
│ SSL certificates     │ Monthly      │ certbot stores in /etc      │
│ Django SECRET_KEY    │ Once + rotate│ Password manager             │
│ Code (git)           │ Per commit   │ GitHub/GitLab (private)     │
└──────────────────────┴──────────────┴────────────────────────────┘

DAILY BACKUP COMMAND:
```bash
#!/bin/bash
# Save as /home/govapp/backup.sh
# Run via cron: 0 2 * * * /home/govapp/backup.sh

BACKUP_DIR="/var/backups/govasset"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d)

# Backup database
pg_dump -U govasset_user -h localhost govasset | gzip > "$BACKUP_DIR/db_$DATE.sql.gz"

# Backup media files
tar -czf "$BACKUP_DIR/media_$DATE.tar.gz" /home/govapp/govasset-platform/media/

# Encrypt and upload to cloud storage
gpg --encrypt --recipient admin@govasset.go.tz "$BACKUP_DIR/db_$DATE.sql.gz"

# Delete backups older than 30 days
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
```
```

<a name="15-10"></a>
### 15.10 Monitoring and Maintenance

**What to monitor:**

```bash
# Check if the service is running
sudo systemctl status gunicorn
sudo systemctl status nginx
sudo systemctl status postgresql

# View logs
sudo journalctl -u gunicorn -n 50 --no-pager      # Gunicorn logs
sudo tail -f /var/log/nginx/access.log             # Nginx access
sudo tail -f /var/log/nginx/error.log              # Nginx errors
sudo tail -f /var/log/gunicorn/error.log           # Django errors

# Database health
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity;" | head -20
sudo -u postgres psql -c "SELECT pg_size_pretty(pg_database_size('govasset'));"

# Server resources
htop                          # CPU + memory
df -h                         # Disk usage
free -h                       # Memory
```

**Set up automatic monitoring (free options):**
- **UptimeRobot** (free): Checks if your site is up every 5 minutes
- **netdata** (self-hosted): Real-time server monitoring dashboard
- **Sentinel** (Django package): Error tracking and performance monitoring
- **Health checks:** `https://govasset.go.tz/health/` endpoint that returns 200

<a name="15-11"></a>
### 15.11 Common Production Issues and Fixes

| Problem | Symptom | Fix |
|---------|---------|-----|
| **502 Bad Gateway** | Nginx cannot reach Gunicorn | `sudo systemctl restart gunicorn`, check if Gunicorn is running |
| **403 Forbidden** | Wrong ALLOWED_HOSTS | Add the domain to ALLOWED_HOSTS in .env |
| **500 Internal Server Error** | Django code error | Check `journalctl -u gunicorn -n 50` |
| **Static files not loading** | collectstatic not run | `python manage.py collectstatic --noinput` |
| **CSS/JS broken** | Wrong STATIC_ROOT or Nginx path | Check STATIC_URL and Nginx alias path |
| **Database connection refused** | PostgreSQL not running | `sudo systemctl restart postgresql` |
| **SSL certificate expired** | Browser shows "Not Secure" | `certbot renew` |
| **Memory exhausted** | Too many Gunicorn workers | Reduce `--workers` in gunicorn.service (formula: 2*CPU_cores + 1) |
| **Slow responses** | No caching, no indexes | Add Redis caching, check slow queries in PostgreSQL |

<a name="15-12"></a>
### 15.12 Production Checklist

```
□ SECURITY
□ DEBUG = False
□ SECRET_KEY stored in environment variable (not code)
□ HTTPS enabled (Let's Encrypt or commercial SSL)
□ ALLOWED_HOSTS configured with real domains
□ Password rotation policy documented
□ Firewall configured (only ports 22, 80, 443 open)

□ DATABASE
□ PostgreSQL (not SQLite)
□ Regular backups configured and tested
□ Database user has limited permissions
□ Connection pooling configured (pgbouncer optional)

□ DEPLOYMENT
□ Gunicorn configured with appropriate workers
□ Nginx configured as reverse proxy
□ Static files served by Nginx
□ Media files served by Nginx
□ Collectstatic run after each deployment

□ MONITORING
□ Health check endpoint working
□ Error logging to files
□ Database backup tested by restoring to a test database
□ Uptime monitoring configured
□ Alert email configured for critical errors

□ DOMAIN
□ DNS records configured (A records, wildcard subdomain)
□ django-tenants Domain records created in database
□ SHOW_PUBLIC_IF_NO_TENANT_FOUND = False
□ Email system configured for password resets
```

<a name="15-13"></a>
### 15.13 Panel Questions for Chapter 15

**Q: Do I need to deploy Keycloak separately?**
A: Yes. Keycloak should run on its own server or be used as a managed service. Running Keycloak on the same server as Django is possible for small deployments but not recommended for production government use.

**Q: How many Gunicorn workers do I need?**
A: The formula is `2 * CPU_cores + 1`. For a 2-CPU server: 5 workers. For a 4-CPU server: 9 workers. More workers = more concurrent requests but also more memory.

**Q: Can I use SQLite in production?**
A: No. SQLite cannot handle concurrent writes. PostgreSQL is required for production with django-tenants. SQLite also does not support schemas, which django-tenants requires.

**Q: How do I handle schema migrations in production?**
A: Run `python manage.py migrate_schemas --executor=parallel` during a maintenance window. This migrates ALL tenant schemas in parallel. For zero-downtime, use a blue-green deployment strategy.

**Q: Should I use Docker for production?**
A: Docker simplifies deployment (everything in containers) but adds complexity in networking and data persistence. For a government project, Docker is recommended to ensure consistent environments across development and production.

**Q: What about government security compliance (e.g., Tanzania e-GA)?**
A: Your infrastructure should comply with Tanzania's e-Government Authority standards. This typically requires: hosting within Tanzania (or with approved providers), regular security audits, data encryption at rest and in transit, access logging, and incident response procedures.

<a name="15-14"></a>
### 15.14 Beginner Misconceptions

**Misconception:** "Production is the same as development, just on a different computer."
**Truth:** Production requires a completely different architecture: multi-process server (Gunicorn), reverse proxy (Nginx), SSL/TLS, environment variables for secrets, managed database, and monitoring. You cannot just copy your code to a server and run `runserver`.

**Misconception:** "Django runserver is good enough for production."
**Truth:** Django's development server is single-process, single-threaded, and insecure. It can handle one request at a time and will crash under load. Gunicorn handles many requests simultaneously and runs as a service that restarts on crash.

**Misconception:** "I need HTTPS for development."
**Truth:** HTTPS is only needed in production (for real user data). Development runs on HTTP over your private hotspot. Adding HTTPS locally is possible but unnecessary.

**Misconception:** "The cloud runs my code itself."
**Truth:** The cloud is just someone else's computer. You still need to configure everything: operating system, database, web server, Python environment, environment variables, and your Django code. "Cloud" doesn't mean "automatic."

**Misconception:** "Once deployed, I don't need to touch it."
**Truth:** Production requires ongoing maintenance: security updates (OS packages, Python packages, Django), database backups, log monitoring, SSL renewal (every 90 days for Let's Encrypt), and responding to incidents.
