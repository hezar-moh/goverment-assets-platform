# Project Structure — Government Asset Platform

## Table of Contents

1. [Overview](#1-overview)
2. [Directory Layout](#2-directory-layout)
3. [Django Apps Deep Dive](#3-django-apps-deep-dive)
   - [3.1 config/](#31-config)
   - [3.2 authentication/](#32-authentication)
   - [3.3 assets/](#33-assets)
   - [3.4 organizations/](#34-organizations)
   - [3.5 tenants/](#35-tenants)
   - [3.6 api/](#36-api)
   - [3.7 dashboard/](#37-dashboard)
   - [3.8 keycloak/](#38-keycloak)
4. [Template Structure](#4-template-structure)
5. [URL Routing Map](#5-url-routing-map)
6. [Database Models](#6-database-models)
7. [Authentication & Authorization](#7-authentication--authorization)
8. [Multi-Tenancy Architecture](#8-multi-tenancy-architecture)
9. [Reorganization Summary](#9-reorganization-summary)

---

## 1. Overview

This is a **multi-tenant government asset management platform** built with Django, django-tenants, and Django REST Framework. Each ministry is a separate PostgreSQL schema (tenant). The platform manages assets, organizational units, master data (funding sources, locations, etc.), and user authentication via Keycloak SSO.

**Technology stack:**

| Layer | Technology |
|-------|-----------|
| Framework | Django 5.x |
| API | Django REST Framework + SimpleJWT |
| Multi-tenancy | django-tenants (schema-based) |
| Auth | Keycloak OIDC + fallback session auth |
| Database | PostgreSQL |
| Tests | pytest + pytest-django |
| ASGI | Daphne / Uvicorn |

---

## 2. Directory Layout

```
D:\government_asset_platform\
├── api/                         # REST API endpoints
│   ├── __init__.py
│   ├── apps.py                  # Django app config
│   ├── asset_views.py           # Asset CRUD API endpoints
│   ├── auth_views.py            # Keycloak login/callback API views
│   ├── org_views.py             # Organization & master data API views
│   ├── exception_handler.py     # Custom DRF exception formatting
│   ├── permissions.py           # Custom DRF permission classes
│   ├── serializers.py           # DRF serializers for all models
│   └── urls.py                  # API route definitions
│
├── assets/                      # Asset & asset category management
│   ├── __init__.py
│   ├── admin.py                 # (empty — custom views used instead)
│   ├── apps.py
│   ├── category_views.py        # Asset category CRUD views (moved from organizations/)
│   ├── models.py                # Asset model (all fields, QR, image, GPS)
│   ├── tests.py                 # Asset tests
│   ├── urls.py                  # Asset + category URL patterns
│   └── views.py                 # Asset CRUD views + helpers
│
├── authentication/              # Auth, users, login, pending access
│   ├── __init__.py
│   ├── admin.py                 # Registers CustomUser only
│   ├── apps.py
│   ├── decorators.py            # login_required_custom, role_required
│   ├── middleware.py             # TenantSessionMiddleware
│   ├── models.py                # CustomUser, PendingAccess, LoginAttempt,
│   │                            # UnlockToken, SuperAdminAuditLog
│   ├── pagination.py            # Pagination helper for admin views
│   ├── pending_access_views.py  # Pending registration review views
│   ├── unlock_views.py          # Account unlock via email token
│   ├── urls.py                  # Auth-related URL patterns
│   ├── user_views.py            # User CRUD, toggle active, reset password
│   ├── views.py                 # Login view, get_client_ip utility
│   ├── tests.py                 # Auth tests
│   └── management/
│       └── commands/
│           ├── setup_demo_data.py          # Seed demo data command
│           └── sync_keycloak_attributes.py # Sync user attrs to Keycloak
│
├── config/                      # Django project configuration
│   ├── __init__.py
│   ├── asgi.py                  # ASGI entry point
│   ├── settings.py              # ALL settings (apps, DB, auth, logging)
│   ├── urls.py                  # Root URL configuration
│   └── wsgi.py                  # WSGI entry point
│
├── dashboard/                   # Dashboard metrics & charts
│   ├── __init__.py
│   ├── apps.py
│   ├── urls.py                  # Dashboard route
│   └── views.py                 # Dashboard stat aggregation view
│
├── docs/                        # Project documentation
│   ├── 01_PROJECT_CONCEPTS_AND_ARCHITECTURE.md
│   ├── 02_KEYCLOAK_AND_AUTHENTICATION.md
│   ├── 03_DEPLOYMENT_LOCAL_AND_RAILWAY.md
│   ├── 04_TESTING_AND_RESPONSIVE_UI.md
│   ├── 05_PRESENTATION_DEFENSE_COMPLETE_GUIDE.md
│   └── PROJECT_STRUCTURE.md     # ← This file
│
├── keycloak/                    # Keycloak SSO integration
│   ├── __init__.py
│   ├── apps.py
│   ├── admin_client.py          # KeycloakAdminService (user sync, roles)
│   └── oidc_backend.py          # KeycloakOIDCBackend (OAuth callback)
│
├── organizations/               # Org units, master data, audit logs
│   ├── __init__.py
│   ├── admin.py                 # (empty — custom views)
│   ├── apps.py
│   ├── master_data_views.py     # Master data CRUD + seed (funding, locations)
│   ├── models.py                # MasterData, OrgUnit, AuditLog
│   ├── tests.py                 # Organization tests
│   ├── urls.py                  # Master data + org unit routes
│   └── views.py                 # OrgUnit CRUD + AuditLog views
│
├── tenants/                     # Ministry (tenant) management
│   ├── __init__.py
│   ├── admin.py                 # Registers Tenant/Ministry
│   ├── apps.py
│   ├── models.py                # Tenant/Ministry model
│   ├── tests.py                 # Tenant tests
│   ├── urls.py                  # Ministry CRUD routes
│   └── views.py                 # Ministry CRUD views (superadmin only)
│
├── templates/                   # All HTML templates
│   ├── assets/                  # (6 templates)
│   ├── authentication/          # (8 templates)
│   ├── dashboard/               # (1 template)
│   ├── organizations/           # (7 templates)
│   ├── shared/                  # (2 templates)
│   └── tenants/                 # (3 templates)
│
├── static/                      # Static assets (CSS, JS, images)
│   └── css/
│       └── style.css            # All custom styles
│
├── manage.py                    # Django management entry point
├── conftest.py                  # Pytest configuration
├── locustfile.py                # Load testing
├── pytest.ini                   # Pytest settings
└── requirements.txt             # Python dependencies
```

---

## 3. Django Apps Deep Dive

### 3.1 config/

**Purpose:** Django project configuration — settings, root URL routing, ASGI/WSGI entry points.

**`config/settings.py`:**

- **`SHARED_APPS`** (apps installed on the public schema): `django.contrib.*`, `rest_framework`, `rest_framework_simplejwt`, `drf_yasg`, `django_tenants`, `tenants`, `authentication`, `keycloak`, `dashboard`, `api`
- **`TENANT_APPS`** (apps installed per tenant schema): `django.contrib.contenttypes`, `django.contrib.auth`, `organizations`, `assets`
- **`TENANT_MODEL`** = `tenants.models.Ministry`
- **Database**: PostgreSQL with django-tenants `TenantSchemaRouter`
- **Auth backends**: `KeycloakOIDCBackend` (primary) + Django `ModelBackend` (fallback)
- **Keycloak settings**: `KEYCLOAK_SERVER_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`, `KEYCLOAK_CLIENT_SECRET`
- **Logging**: Separate loggers for `authentication` and `keycloak` modules
- **REST Framework**: JWT auth (`JWTAuthentication`) + session auth; custom exception handler at `api.exception_handler.custom_exception_handler`

**`config/urls.py`:**

Root URL routing delegates to per-app URL configs:

| Prefix | Included from | Purpose |
|--------|--------------|---------|
| `""` | `authentication.urls` | Login, logout, user mgmt, pending access, unlock |
| `""` | `assets.urls` | Asset list/create, category list/create |
| `""` | `organizations.urls` | Master data, org units, audit logs |
| `""` | `tenants.urls` | Ministry CRUD |
| `""` | `dashboard.urls` | Dashboard |
| `"api/"` | `api.urls` | REST API endpoints |

### 3.2 authentication/

**Purpose:** Handles all user-facing authentication, user management, pending registration, account unlock, and audit logging for superadmin actions.

**Files:**

| File | Contents | Key Functions/Classes |
|------|----------|----------------------|
| `models.py` | 5 models | `CustomUser` (extends AbstractUser with role, ministry_schema, keycloak_id, lockout fields), `PendingAccess` (registration requests), `LoginAttempt` (lockout tracking), `UnlockToken` (email-based unlock), `SuperAdminAuditLog` (superadmin actions) |
| `views.py` | Login view + utility | `login_view` — validates credentials against Django + Keycloak, enforces progressive lockout; `get_client_ip` — extracts real IP from proxy headers |
| `user_views.py` | 7+ view functions | `user_list_view`, `user_create_view`, `user_edit_view`, `user_toggle_active_view`, `user_reset_password_view` — all MINISTRY_ADMIN views for managing users; `_send_welcome_email`, `_sync_to_keycloak`, `_log_user_action` helpers; imports `KeycloakAdminService` from `keycloak.admin_client` |
| `pending_access_views.py` | 2 views | `pending_access_list_view` (superadmin sees all pending), `pending_access_review_view` (approve/reject with email notification) |
| `unlock_views.py` | 2 views | `unlock_request_view` (sends unlock email), `unlock_confirm_view` (validates token, unlocks account) |
| `decorators.py` | 2 decorators | `login_required_custom` — checks session + Keycloak token validity with tenant schema; `role_required(*roles)` — restricts by user role field |
| `middleware.py` | 1 middleware | `TenantSessionMiddleware` — sets tenant schema on login and clears on logout |
| `pagination.py` | 1 helper | `paginate_queryset(request, qs, per_page=10)` — generic pagination for admin list views |
| `admin.py` | Registers `CustomUser` only | Other models managed through custom views |
| `management/commands/setup_demo_data.py` | Management command | `python manage.py setup_demo_data` — creates 3 ministries (Education, Health, Agriculture) with admins, org units, master data, asset categories, and sample assets |
| `management/commands/sync_keycloak_attributes.py` | Management command | `python manage.py sync_keycloak_attributes` — syncs all user attributes (role, ministry) to Keycloak |

**Key flows:**

1. **Login flow**: `login_view` → validates against Django auth → if Keycloak enabled, validates against Keycloak → checks lockout status → records `LoginAttempt` → creates session → redirects to dashboard
2. **Registration flow**: User registers → `PendingAccess` created → superadmin reviews in `pending_access_review_view` → approves (creates `CustomUser`) or rejects (with reason email)
3. **Unlock flow**: `unlock_request_view` → sends email with token → `unlock_confirm_view` validates `UnlockToken` → resets failed attempts

### 3.3 assets/

**Purpose:** Manages physical/government assets and their categories. This is the core business domain.

**Files:**

| File | Contents |
|------|----------|
| `models.py` | `Asset` model — 30+ fields including: `asset_number` (auto-generated), `name`, `description`, `category` (FK to `AssetCategory`), `serial_number`, `model`, `manufacturer`, `purchase_date`, `purchase_cost`, `funding_source`, `acquisition_method`, `cost_centre`, `location`, `org_unit`, `custodian`, `status` (ACTIVE/DISPOSED/MAINTENANCE/PLANNED), `condition`, `asset_image`, `qr_code`, `latitude`, `longitude`, `expiry_date`, `disposal_date`, `disposal_method` |
| `views.py` | `asset_list_view` (with category/status/search filters + export), `asset_create_view` (with QR generation), `asset_detail_view`, `asset_edit_view`, `asset_delete_view`; helpers: `_get_client_ip`, `_load_asset_form_data`, `generate_asset_number`, `_log_asset_action` |
| `category_views.py` | `asset_category_list_view`, `asset_category_create_view`, `asset_category_edit_view`, `asset_category_delete_view` — moved from `organizations/master_data_views.py` during reorganization |
| `urls.py` | Routes for assets (`/assets/`, `/assets/create/`, `/assets/<id>/`, etc.) and categories (`/assets/categories/`, `/assets/categories/create/`, etc.) |

### 3.4 organizations/

**Purpose:** Manages organizational structure (org units/departments), master data (dropdown values like funding sources, locations), and audit logs.

**Files:**

| File | Contents |
|------|----------|
| `models.py` | `MasterData` — generic key-value with category (FUNDING_SOURCE, ACQUISITION_METHOD, LOCATION_TYPE, DISPOSAL_METHOD, COST_CENTRE), value code, display label, sort order; `OrgUnit` — tree hierarchy (parent FK), name, code, head; `AuditLog` — generic action log (CREATE/UPDATE/DELETE) for all tenant models |
| `views.py` | `org_unit_list_view`, `org_unit_create_view`, `org_unit_edit_view`, `org_unit_delete_view`; `audit_log_list_view`, `audit_log_detail_view` |
| `master_data_views.py` | `master_data_list_view`, `master_data_create_view`, `master_data_edit_view`, `master_data_delete_view`, `master_data_seed_view` (loads defaults for 7 categories × 4-7 items each) |
| `urls.py` | Routes for master data (`/master-data/`, etc.), org units (`/org-units/`, etc.), audit logs (`/audit-logs/`, etc.) |

**Note:** Asset category views were originally in `master_data_views.py` but have been moved to `assets/category_views.py` to match app responsibility.

### 3.5 tenants/

**Purpose:** Manages ministries (tenants). Superadmin-only CRUD.

**Files:**

| File | Contents |
|------|----------|
| `models.py` | `Ministry` (extends `TenantMixin`) — fields: `schema_name`, `name`, `code`, `domain_url`, `is_active`, `address`, `phone`, `email`, `logo`; `paid_until` date, `on_trial` bool |
| `views.py` | `ministry_list_view`, `ministry_create_view`, `ministry_detail_view`, `ministry_edit_view`, `ministry_toggle_active_view` — all decorated with `@superadmin_required` |
| `urls.py` | Routes for ministries (`/ministries/`, etc.) |
| `admin.py` | Registers `Ministry` with django-tenants admin |

### 3.6 api/

**Purpose:** REST API endpoints for external integration and AJAX calls from the frontend.

**Files:**

| File | Contents |
|------|----------|
| `asset_views.py` | `AssetListCreateAPIView` (GET list + POST create), `AssetRetrieveUpdateDestroyAPIView` (GET/PUT/PATCH/DELETE by ID) |
| `auth_views.py` | `KeycloakLoginView` (returns Keycloak auth URL), `KeycloakCallbackView` (handles OAuth callback, creates user if new, returns JWT) |
| `org_views.py` | `MasterDataAPIView` (GET list by category) |
| `serializers.py` | `AssetSerializer`, `UserSerializer`, `MasterDataSerializer`, `KeycloakLoginSerializer`, `KeycloakCallbackSerializer` |
| `permissions.py` | `IsSuperAdmin`, `IsMinistryAdmin`, `IsAuthenticatedAndTenantMember` |
| `exception_handler.py` | `custom_exception_handler` — standardizes error format across all API responses |
| `urls.py` | Routes under `/api/`: assets CRUD, auth, master data |

### 3.7 dashboard/

**Purpose:** Aggregated metrics and statistics displayed on the landing page after login.

**Files:**

| File | Contents |
|------|----------|
| `views.py` | `dashboard_view` — computes: total assets, assets by status, assets by category, active vs disposed ratio, recent additions, expiry warnings (within 90 days), assets by org unit; uses `schema_context` |
| `urls.py` | Single route: `/` → `dashboard_view` |
| `apps.py` | `DashboardConfig` with `verbose_name = "Dashboard"` |

### 3.8 keycloak/

**Purpose:** All Keycloak SSO integration code. Separated from `authentication/` for modularity.

**Files:**

| File | Contents |
|------|----------|
| `admin_client.py` | `KeycloakAdminService` — Wraps Keycloak admin REST API. Methods: `create_user`, `update_user`, `sync_attributes`, `get_user_by_username`, `reset_password`, `assign_role`, `remove_role`, `deactivate_user`, `activate_user`. Uses OAuth2 client credentials grant for admin access. |
| `oidc_backend.py` | `KeycloakOIDCBackend` — Custom Django auth backend. `authenticate()` method validates access token via Keycloak well-known JWKS endpoint, creates/updates local user, sets tenant schema. Used as primary auth backend in settings. |

---

## 4. Template Structure

All templates are in `templates/` with 6 subdirectories mirroring the app structure:

```
templates/
├── assets/
│   ├── asset_list.html              # Asset list with search, filter, export
│   ├── asset_form.html              # Asset creation form (30+ fields)
│   ├── asset_detail.html            # Full asset detail with QR, image, map
│   ├── asset_category_list.html     # Category management grid
│   ├── asset_category_form.html     # Category creation form
│   └── asset_category_edit.html     # Category edit form
│
├── authentication/
│   ├── login.html                   # Login form
│   ├── user_list.html               # User list (ministry admin)
│   ├── user_form.html               # User creation form
│   ├── user_edit.html               # User edit form
│   ├── user_reset_password.html     # Password reset for users
│   ├── pending_access_list.html     # Pending registrations (superadmin)
│   ├── pending_access_review.html   # Approve/reject registration
│   └── unlock_result.html          # Unlock confirmation
│
├── dashboard/
│   └── dashboard.html               # Main dashboard with cards + charts
│
├── organizations/
│   ├── master_data_list.html        # Master data grouped by category
│   ├── master_data_form.html        # Add master data entry
│   ├── master_data_edit.html        # Edit master data entry
│   ├── org_unit_list.html           # Org unit tree
│   ├── org_unit_form.html           # Add org unit
│   ├── org_unit_edit.html           # Edit org unit
│   ├── audit_log.html               # Audit log list with filters
│   └── audit_log_detail.html        # Single audit entry detail
│
├── shared/
│   ├── base.html                    # Main layout: header, sidebar, footer, JS
│   └── pagination.html              # Reusable page number buttons
│
└── tenants/
    ├── ministry_list.html           # Ministry list (superadmin)
    ├── ministry_form.html           # Create ministry
    └── ministry_detail.html         # Ministry detail
```

All templates extend `shared/base.html` which provides:
- Responsive sidebar navigation (auto-highlights current app)
- User info + role badge in header
- Django messages rendering
- Common JS libraries
- Role-based menu visibility

---

## 5. URL Routing Map

### From root (`config/urls.py`):

| URL Pattern | View | Name | Decorators |
|-------------|------|------|------------|
| **authentication/** | | | |
| `""` (login) | `authentication.views.login_view` | `login` | — |
| `"logout/"` | `django.contrib.auth.views.logout_then_login` | `logout` | — |
| `"users/"` | `authentication.user_views.user_list_view` | `user_list` | MINISTRY_ADMIN |
| `"users/create/"` | `authentication.user_views.user_create_view` | `user_create` | MINISTRY_ADMIN |
| `"users/<id>/edit/"` | `authentication.user_views.user_edit_view` | `user_edit` | MINISTRY_ADMIN |
| `"users/<id>/toggle-active/"` | `authentication.user_views.user_toggle_active_view` | `user_toggle_active` | MINISTRY_ADMIN |
| `"users/<id>/reset-password/"` | `authentication.user_views.user_reset_password_view` | `user_reset_password` | MINISTRY_ADMIN |
| `"pending-access/"` | `authentication.pending_access_views.pending_access_list_view` | `pending_access_list` | SUPERADMIN |
| `"pending-access/<id>/review/"` | `authentication.pending_access_views.pending_access_review_view` | `pending_access_review` | SUPERADMIN |
| `"unlock-request/"` | `authentication.unlock_views.unlock_request_view` | `unlock_request` | — |
| `"unlock/<uidb64>/<token>/"` | `authentication.unlock_views.unlock_confirm_view` | `unlock_confirm` | — |
| **assets/** | | | |
| `"assets/"` | `assets.views.asset_list_view` | `asset_list` | MINISTRY_ADMIN |
| `"assets/create/"` | `assets.views.asset_create_view` | `asset_create` | MINISTRY_ADMIN |
| `"assets/<id>/"` | `assets.views.asset_detail_view` | `asset_detail` | MINISTRY_ADMIN |
| `"assets/<id>/edit/"` | `assets.views.asset_edit_view` | `asset_edit` | MINISTRY_ADMIN |
| `"assets/<id>/delete/"` | `assets.views.asset_delete_view` | `asset_delete` | MINISTRY_ADMIN |
| `"assets/categories/"` | `assets.category_views.asset_category_list_view` | `asset_category_list` | MINISTRY_ADMIN |
| `"assets/categories/create/"` | `assets.category_views.asset_category_create_view` | `asset_category_create` | MINISTRY_ADMIN |
| `"assets/categories/<id>/edit/"` | `assets.category_views.asset_category_edit_view` | `asset_category_edit` | MINISTRY_ADMIN |
| `"assets/categories/<id>/delete/"` | `assets.category_views.asset_category_delete_view` | `asset_category_delete` | MINISTRY_ADMIN |
| **organizations/** | | | |
| `"master-data/"` | `organizations.master_data_views.master_data_list_view` | `master_data_list` | MINISTRY_ADMIN |
| `"master-data/create/"` | `organizations.master_data_views.master_data_create_view` | `master_data_create` | MINISTRY_ADMIN |
| `"master-data/<id>/edit/"` | `organizations.master_data_views.master_data_edit_view` | `master_data_edit` | MINISTRY_ADMIN |
| `"master-data/<id>/delete/"` | `organizations.master_data_views.master_data_delete_view` | `master_data_delete` | MINISTRY_ADMIN |
| `"master-data/seed/"` | `organizations.master_data_views.master_data_seed_view` | `master_data_seed` | MINISTRY_ADMIN |
| `"org-units/"` | `organizations.views.org_unit_list_view` | `org_unit_list` | MINISTRY_ADMIN |
| `"org-units/create/"` | `organizations.views.org_unit_create_view` | `org_unit_create` | MINISTRY_ADMIN |
| `"org-units/<id>/edit/"` | `organizations.views.org_unit_edit_view` | `org_unit_edit` | MINISTRY_ADMIN |
| `"org-units/<id>/delete/"` | `organizations.views.org_unit_delete_view` | `org_unit_delete` | MINISTRY_ADMIN |
| `"audit-logs/"` | `organizations.views.audit_log_list_view` | `audit_log_list` | MINISTRY_ADMIN |
| `"audit-logs/<id>/"` | `organizations.views.audit_log_detail_view` | `audit_log_detail` | MINISTRY_ADMIN |
| **tenants/** | | | |
| `"ministries/"` | `tenants.views.ministry_list_view` | `ministry_list` | SUPERADMIN |
| `"ministries/create/"` | `tenants.views.ministry_create_view` | `ministry_create` | SUPERADMIN |
| `"ministries/<id>/"` | `tenants.views.ministry_detail_view` | `ministry_detail` | SUPERADMIN |
| `"ministries/<id>/edit/"` | `tenants.views.ministry_edit_view` | `ministry_edit` | SUPERADMIN |
| `"ministries/<id>/toggle-active/"` | `tenants.views.ministry_toggle_active_view` | `ministry_toggle_active` | SUPERADMIN |
| **dashboard/** | | | |
| `""` | `dashboard.views.dashboard_view` | `dashboard` | Requires login |
| **api/** | | | |
| `"api/assets/"` | `api.asset_views.AssetListCreateAPIView` | `asset-list-create` | JWT + IsAuthenticated |
| `"api/assets/<id>/"` | `api.asset_views.AssetRetrieveUpdateDestroyAPIView` | `asset-detail` | JWT + IsAuthenticated |
| `"api/auth/login/"` | `api.auth_views.KeycloakLoginView` | `keycloak-login` | — |
| `"api/auth/callback/"` | `api.auth_views.KeycloakCallbackView` | `keycloak-callback` | — |
| `"api/master-data/"` | `api.org_views.MasterDataAPIView` | `master-data-api` | JWT + IsAuthenticated |

---

## 6. Database Models

### SHARED_SCHEMA models (public schema):

| Model | Table | Key Fields | Purpose |
|-------|-------|------------|---------|
| `Ministry` (tenants) | `tenants_ministry` | `schema_name`, `name`, `code`, `domain_url`, `is_active`, `paid_until`, `on_trial` | Each ministry = one tenant schema |
| `CustomUser` (authentication) | `authentication_customuser` | `username`, `email`, `role` (SUPERADMIN/MINISTRY_ADMIN/STAFF), `ministry_schema`, `keycloak_id`, `failed_login_attempts`, `locked_until` | All users across all ministries |
| `PendingAccess` (authentication) | `authentication_pendingaccess` | `email`, `full_name`, `ministry_name`, `reason`, `status`, `admin_notes` | Registration requests awaiting approval |
| `LoginAttempt` (authentication) | `authentication_loginattempt` | `username`, `ip_address`, `timestamp`, `successful` | Progressive lockout tracking |
| `UnlockToken` (authentication) | `authentication_unlocktoken` | `user`, `token`, `created_at`, `expires_at`, `used` | Email-based account unlock |
| `SuperAdminAuditLog` (authentication) | `authentication_superadminauditlog` | `admin_user`, `action`, `target_user`, `details`, `timestamp`, `ip_address` | Audit trail for superadmin actions |

### TENANT_SCHEMA models (per ministry):

| Model | Table | Key Fields | Purpose |
|-------|-------|------------|---------|
| `Asset` (assets) | `assets_asset` | `asset_number`, `name`, `category`, `serial_number`, `status`, `purchase_cost`, `org_unit`, `custodian`, `asset_image`, `qr_code`, `latitude`, `longitude` | Full asset inventory |
| `AssetCategory` (assets) | `assets_assetcategory` | `name`, `description` | Categorization of assets |
| `MasterData` (organizations) | `organizations_masterdata` | `category` (choice), `value` (code), `label`, `sort_order`, `is_active` | Configurable dropdown values |
| `OrgUnit` (organizations) | `organizations_orgunit` | `name`, `code`, `parent` (self-FK) | Organizational hierarchy |
| `AuditLog` (organizations) | `organizations_auditlog` | `action`, `model_name`, `object_id`, `old_value`, `new_value`, `performed_by`, `ip_address` | All tenant-level data changes |

---

## 7. Authentication & Authorization

### Authentication Flow

```
User → Login Page → login_view
  ├── Check progressive lockout (LoginAttempt model)
  ├── Validate password (Django ModelBackend)
  ├── If Keycloak enabled: validate against Keycloak OIDC
  │   └── KeycloakOIDCBackend.authenticate()
  │       └── Verify JWT via JWKS endpoint
  ├── Record LoginAttempt (success/failure)
  ├── Update failed_login_attempts / locked_until on CustomUser
  ├── Set schema via TenantSessionMiddleware
  └── Redirect to dashboard
```

### Role System

| Role | Access Level |
|------|-------------|
| `SUPERADMIN` | All tenants, ministry management, pending access review, superadmin audit log |
| `MINISTRY_ADMIN` | Single tenant: full CRUD on assets, categories, master data, org units, users |
| `STAFF` | Single tenant: read-only or limited access (configurable per view) |

### Authorization Decorators

- `@login_required_custom` — checks Django session + optional Keycloak token refresh; sets tenant schema on request
- `@role_required("SUPERADMIN")` — restricts to superadmins only
- `@role_required("MINISTRY_ADMIN")` — restricts to ministry admins (includes superadmins via role hierarchy)
- "superadmin_required" — custom check used in tenants/views.py

### API Authentication

- JWT tokens via `rest_framework_simplejwt`
- Keycloak OAuth2 flow for external clients
- Custom `IsSuperAdmin`, `IsMinistryAdmin`, `IsAuthenticatedAndTenantMember` permission classes

---

## 8. Multi-Tenancy Architecture

The project uses **django-tenants** with **schema-based isolation**:

```
PostgreSQL Database
├── public schema
│   ├── tenants_ministry           # Ministry definitions
│   ├── authentication_customuser  # All users
│   ├── authentication_*           # Auth models
│   └── keycloak_*                 # (app code only, no DB tables)
│
├── ministry_education schema
│   ├── assets_asset               # Education ministry's assets
│   ├── assets_assetcategory
│   ├── organizations_masterdata
│   ├── organizations_orgunit
│   ├── organizations_auditlog
│   └── django_*                   # Django auth, contenttypes
│
├── ministry_health schema
│   └── (same structure as education)
│
└── ministry_agriculture schema
    └── (same structure as above)
```

**Key mechanism:** `TenantSessionMiddleware` sets `connection.set_tenant(ministry)` on login. All queries in tenant apps automatically route to the correct schema. `schema_context(tenant_schema_name)` is used for cross-schema operations (e.g., in `setup_demo_data`).

---

## 9. Reorganization Summary

The project was recently reorganized to ensure **every function lives in the app its name suggests**. Before, `authentication/` contained API views, dashboard views, and Keycloak admin code. `organizations/master_data_views.py` contained asset category views. The reorganization:

| What | From | To |
|------|------|----|
| API views (DRF) | `authentication/api_views.py`, `assets/api_views.py`, `organizations/api_views.py` | `api/asset_views.py`, `api/auth_views.py`, `api/org_views.py` |
| API permissions | `authentication/api_permissions.py` | `api/permissions.py` |
| API serializers | `authentication/api_serializers.py` | `api/serializers.py` |
| API exception handler | `authentication/api_exception_handler.py` | `api/exception_handler.py` |
| API URLs | `authentication/api_urls.py` | `api/urls.py` |
| Dashboard | `authentication/dashboard_views.py` | `dashboard/views.py` |
| Keycloak admin client | `authentication/keycloak_admin.py` | `keycloak/admin_client.py` |
| Keycloak OIDC backend | `authentication/oidc_backend.py` | `keycloak/oidc_backend.py` |
| Asset category views | `organizations/master_data_views.py` | `assets/category_views.py` |
| Asset category templates | `templates/organizations/asset_category_*.html` | `templates/assets/asset_category_*.html` |
| Asset category URLs | `master-data/categories/...` | `assets/categories/...` |
| Documentation | `01_*.md`, `02_*.md` in root | `docs/01_*.md`, `docs/02_*.md` |

All imports, URL routing, and template references were updated. The project passes `python manage.py check` with zero issues.
