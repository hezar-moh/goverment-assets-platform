# GOVERNMENT ASSET PLATFORM — Testing & Responsive UI

> **Purpose:** Complete testing guide (5 testing types, 83 unit tests, 13 API tests) + complete documentation of the responsive UI changes for mobile/tablet support.

---

## Table of Contents

- [1. Testing Overview — 5 Types](#1-testing-overview--5-types)
- [2. Unit Tests (pytest) — 83 Tests Across 4 Apps](#2-unit-tests-pytest--83-tests-across-4-apps)
- [3. Integration Tests (Postman) — 13 API Tests](#3-integration-tests-postman--13-api-tests)
- [4. Load Tests (Locust) — 50 Concurrent Users](#4-load-tests-locust--50-concurrent-users)
- [5. Security Tests (OWASP ZAP)](#5-security-tests-owasp-zap)
- [6. Functional Tests (Manual Checklist)](#6-functional-tests-manual-checklist)
- [7. Responsive UI — Overview & Changes](#7-responsive-ui--overview--changes)
- [8. Responsive UI — Complete Attribute Inventory](#8-responsive-ui--complete-attribute-inventory)
- [9. Responsive UI — Panel Q&A](#9-responsive-ui--panel-qa)

---

## 1. Testing Overview — 5 Types

| Test Type | Tool | What it checks | How to run |
|-----------|------|---------------|------------|
| **Unit** | pytest | Individual functions, properties, permissions | `python -m pytest` |
| **Integration** | Postman | Full login → API data flow | Import `postman_collection.json` → Run |
| **Load** | Locust | Performance under 50 concurrent users | `locust -f locustfile.py` |
| **Security** | OWASP ZAP | Vulnerability scanning (XSS, SQL injection, etc.) | Open ZAP → Automated scan |
| **Functional** | Manual checklist | Requirements verification | Follow checklist below |

### Config Files

**`pytest.ini`** — Tells pytest where to find tests:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py
testpaths = authentication assets organizations tenants
```

**`conftest.py`** — Registers test modules as pytest plugins:
```python
pytest_plugins = [
    'assets.tests', 'authentication.tests',
    'organizations.tests', 'tenants.tests',
]
```

---

## 2. Unit Tests (pytest) — 83 Tests Across 4 Apps

### 2.1 TenantTestCase vs TestCase

This project uses `django-tenants`, so some tests need a real tenant schema.

| Base class | When to use | Why |
|------------|-------------|-----|
| `TestCase` | Testing shared-schema models (`CustomUser`, `Ministry`, `PendingAccess`) | Tables are in `public` schema |
| `TenantTestCase` | Testing tenant-schema models (`Asset`, `AuditLog`, `OrgUnit`, `MasterData`) | Needs a real tenant schema created |

`TenantTestCase` automatically:
1. Creates a `Ministry` record (e.g., schema_name = `'test_assets'`)
2. Saves it — auto-creates PostgreSQL schema + runs migrations for tenant apps
3. Sets connection to that schema
4. After all tests, drops the schema

We define `setup_tenant()` to set required fields:
```python
@classmethod
def setup_tenant(cls, tenant):
    tenant.name = "Test Ministry"
    tenant.short_name = "TST"
```

### 2.2 `authentication/tests.py` (42 tests)

**What it tests:** User roles, permission classes, brute-force lockout, unlock tokens.

**Example — PermissionClassesTest:**
```python
def setUp(self):
    # Creates 5 users — one for each role
    self.super_admin = CustomUser.objects.create_user(
        username='super', role='SUPER_ADMIN', ministry_schema=None)
    self.ministry_admin = CustomUser.objects.create_user(
        username='admin', role='MINISTRY_ADMIN', ministry_schema='moh_schema')
    # ... agency_manager, facility_clerk, auditor

def test_is_super_admin_allows_super_admin(self):
    perm = IsSuperAdmin()
    request = Mock(user=self.super_admin, method='GET')
    self.assertTrue(perm.has_permission(request, None))

def test_is_super_admin_blocks_facility_clerk(self):
    perm = IsSuperAdmin()
    request = Mock(user=self.facility_clerk, method='GET')
    self.assertFalse(perm.has_permission(request, None))
```

**Example — brute-force lockout:**
```python
def test_locked_during_cooldown(self):
    attempt = LoginAttempt.objects.create(
        username='testuser', stage='LOCKED',
        locked_until=timezone.now() + timedelta(minutes=10))
    self.assertTrue(attempt.is_locked)
```

### 2.3 `assets/tests.py` (21 tests)

**What it tests:** Asset expiry dates, warranty tracking, auto-numbering, status choices.

Two classes:
- `AssetModelTests(TenantTestCase)` — tests that need a tenant schema
- `AssetSchemaIndependentTests(TestCase)` — tests that only look at model meta

**Example — expiry date:**
```python
def test_is_expired_true_when_date_in_past(self):
    category = AssetCategory.objects.create(name='Test', code='TST')
    asset = Asset.objects.create(
        asset_number='TST-TST-2026-0001', name='Test Asset',
        category=category,
        asset_expiry_date=timezone.now().date() - timedelta(days=1),
        status='ACTIVE')
    self.assertTrue(asset.is_expired)
```

**Example — asset number generation:**
```python
def test_first_asset_number_starts_at_0001(self):
    from assets.views import generate_asset_number
    AssetCategory.objects.create(name='ICT', code='ICT')
    prefix = self.tenant.schema_name.replace("_schema", "").upper()[:3]
    number = generate_asset_number(self.tenant.schema_name, 'ICT')
    self.assertRegex(number, rf'^{prefix}-ICT-\d{{4}}-0001$')
```

### 2.4 `organizations/tests.py` (17 tests)

**What it tests:** Audit log tamper protection, OrgUnit hierarchy, MasterData constraints.

**Example — tamper-proof audit log:**
```python
def test_cannot_update_existing_audit_log(self):
    log = AuditLog.objects.create(
        performed_by_id=1, performed_by_name='Test User',
        action='CREATE', model_name='Asset',
        object_id='1', object_repr='MOH-ICT-2026-0001',
        ip_address='127.0.0.1')
    log.object_repr = 'Changed value'
    with self.assertRaises(PermissionError):
        log.save()
```

**Example — OrgUnit hierarchy:**
```python
def test_facility_full_path(self):
    ministry = OrgUnit.objects.create(name='MOH', code='MOH', unit_type='MINISTRY')
    agency = OrgUnit.objects.create(name='MNH', code='MNH', unit_type='AGENCY', parent=ministry)
    facility = OrgUnit.objects.create(name='RAD', code='RAD', unit_type='FACILITY', parent=agency)
    self.assertEqual(facility.get_full_path(),
                     'MOH > MNH > RAD')
```

### 2.5 `tenants/tests.py` (3 tests)

```python
def test_ministry_string(self):
    ministry = Ministry.objects.create(name='MOH', short_name='MOH', schema_name='moh_schema')
    self.assertEqual(str(ministry), 'MOH (moh_schema)')
```

### 2.6 Running Tests

```bash
# Run ALL 83 tests
python -m pytest

# Run just one file with verbose output
python -m pytest authentication/tests.py -v

# Run just one test class
python -m pytest assets/tests.py::AssetModelTests -v

# Run just one test method
python -m pytest authentication/tests.py::PermissionClassesTest::test_is_super_admin_allows_super_admin -v

# Show slowest tests (useful for optimization)
python -m pytest --durations=5
```

---

## 3. Integration Tests (Postman) — 13 API Tests

### 3.1 Collection Structure

The `postman_collection.json` file contains 13 requests in 3 folders:

```
Authentication (5 tests)
  1. Login          → POST /api/auth/login/
  2. Get My Profile → GET  /api/auth/me/
  3. Verify Token   → GET  /api/auth/verify-token/
  4. Reject unauth  → GET  /api/auth/me/  (NO token — expects 401)
  5. Refresh Token  → POST /api/auth/refresh/

Assets (5 tests)
  6. List Assets       → GET    /api/assets/
  7. Create Asset      → POST   /api/assets/
  8. Get Asset Detail  → GET    /api/assets/{id}/
  9. Update Asset      → PUT    /api/assets/{id}/
  10. Delete Asset     → DELETE /api/assets/{id}/

Organisation & Dashboard (3 tests)
  11. List Org Units   → GET /api/org-units/
  12. View Audit Logs  → GET /api/audit-logs/
  13. Dashboard Stats  → GET /api/dashboard/stats/
```

### 3.2 How Variables Flow Between Tests

Postman uses **collection variables** — global variables all requests can read/write:

1. **Login test** succeeds → saves `access` token to `{{access_token}}`
2. **Every subsequent request** uses `Authorization: Bearer {{access_token}}`
3. **Create Asset test** saves the new asset's ID to `{{asset_id}}`
4. **Get/Update/Delete Asset** use `{{asset_id}}` in the URL

### 3.3 Test Assertions

Each request has JavaScript that runs after the response:
```javascript
pm.test('Login successful', function () {
    pm.response.to.have.status(200);
    var jsonData = pm.response.json();
    pm.expect(jsonData.access).to.not.be.empty;
});
```

---

## 4. Load Tests (Locust) — 50 Concurrent Users

### 4.1 What It Simulates

50 virtual ministry staff using the platform simultaneously.

| Task | Weight | Frequency |
|------|--------|-----------|
| List assets | 5 | Most common |
| View asset detail | 3 | Common |
| View audit logs | 2 | Moderate |
| View dashboard stats | 2 | Moderate |
| View profile | 1 | Least |
| Verify token | 1 | Least |
| Refresh token | 1 | Least |

### 4.2 How to Run

```bash
# Install locust if not already installed
pip install locust

# Start the load test
locust -f locustfile.py
```

Open `http://localhost:8089` in browser → Enter:
- **Number of users:** 50
- **Spawn rate:** 10 users/second
- Click "Start swarming"

### 4.3 What to Check

- **Response times** — should be <500ms for most requests
- **Error rate** — should be <1%
- **Requests per second** — how many the system can handle
- **90th percentile** — the response time that 90% of requests are faster than

### 4.4 Weight System Explained

```python
@task(5)  # Runs 5x more often than @task(1)
def list_assets(self): ...

@task(1)  # Runs 1x
def view_profile(self): ...
```

Out of every ~15 tasks a user performs:
- 5 = list assets
- 3 = view asset detail
- 2 = view audit logs
- 2 = view dashboard
- 1 = view profile
- 1 = verify token
- 1 = refresh token

---

## 5. Security Tests (OWASP ZAP)

### 5.1 How to Run

1. Download and install OWASP ZAP from `https://www.zaproxy.org/download/`
2. Open ZAP → "Automated Scan" → Enter URL (e.g., `http://localhost:8000`)
3. Click "Attack"
4. ZAP crawls the site and tests for vulnerabilities

### 5.2 What It Checks For

| Vulnerability | What it means | How we prevent it |
|--------------|-------------|-------------------|
| SQL Injection | Malicious SQL in input fields | Django ORM parameterizes all queries |
| XSS (Cross-Site Scripting) | Malicious scripts in output | Django template engine auto-escapes HTML |
| CSRF (Cross-Site Request Forgery) | Forged requests from other sites | CSRF tokens on all forms |
| Security Headers | Missing protection headers | Set in settings.py |
| Information Disclosure | Sensitive data in error pages | `DEBUG=False` in production |

---

## 6. Functional Tests (Manual Checklist)

Use this checklist before presentations or after major changes:

- [ ] Login page loads at `/login/`
- [ ] Keycloak SSO login works (redirect → login → callback → dashboard)
- [ ] API login works: `POST /api/auth/login/` returns JWT
- [ ] Dashboard shows correct statistics (counts, expiry warnings)
- [ ] Asset list loads with correct data + filters work
- [ ] Create new asset succeeds (auto-number generated)
- [ ] Edit asset succeeds (field-level audit logged)
- [ ] Delete asset works (with confirmation)
- [ ] Asset expiry warnings show correctly (90 days, 30 days, expired)
- [ ] Audit log shows all actions (create, update, delete, login)
- [ ] User management: create / edit / activate / deactivate user
- [ ] Role-based access: AUDITOR cannot create/edit/delete assets
- [ ] Multi-tenancy: MOH user cannot see MOF data
- [ ] Mobile API endpoints return correct JSON
- [ ] JWT token refresh works (access expired → refresh → new access)
- [ ] Account lockout: 5 failed attempts → 429 error
- [ ] Swagger API docs load at `/swagger/`
- [ ] Responsive UI works on small screens (sidebar hamburger, login form)
- [ ] Admin panel at `/admin/` loads and works
- [ ] pgAdmin can connect to database

---

## 7. Responsive UI — Overview & Changes

### 7.1 The Problem (Before)

The entire UI was **desktop-only**. On a phone:

- **Login page** — branding panel and form panel sat side-by-side. Form panel was 460px wide, wider than most phone screens.
- **Sidebar** — fixed at 260px, always visible. On a 375px iPhone, it consumed 69% of the screen.
- **All forms** — used two-column grids (`1fr 300px`) with no media queries.
- **No media queries** — zero `@media` rules in the entire CSS file (758 lines).
- **No touch support** — buttons were small (32-36px), hover effects that never resolve.

### 7.2 Files Changed

| File | What was added |
|------|---------------|
| `static/css/style.css` | Hamburger toggle, sidebar overlay, login-outer wrapper, 2 media query blocks (`<900px`, `<480px`), touch optimisation — **202 new lines** |
| `templates/shared/base.html` | Hamburger button in topbar (line 125), sidebar overlay div (line 117), JavaScript toggle function (lines 166-171) |
| `templates/authentication/login.html` | Added `login-outer` CSS class to the outer container (line 5) |

### 7.3 The Two Breakpoints

```
  0px         480px        900px               1920px
  ├─────────────┼─────────────┼─────────────────────┤
  │  PHONE      │   TABLET    │      DESKTOP        │
  │ Single-col  │ Compact     │ Full layout          │
  │ Sidebar     │ Sidebar     │ Sidebar always       │
  │ hidden      │ hidden      │ visible              │
```

**At 900px and below (tablets + phones):**
- Sidebar slides off-screen via `transform: translateX(-100%)`
- Hamburger button (☰) appears in top-left
- Dark semi-transparent overlay appears behind sidebar when open
- Login branding panel hidden, form goes full-width
- Two-column forms collapse to single column (`grid-template-columns: 1fr !important`)
- Dashboard stat cards shrink minimum from 200px to 140px
- Page headers stack vertically (title above buttons)

**At 480px and below (small phones):**
- Stat cards become single column (`grid-template-columns: 1fr`)
- Filter inputs go full width (`min-width: 100%`)
- Button fonts shrink slightly (`13px`, padding `8px 12px`)
- Table cells get less padding

**Touch devices (detected via `@media (hover: none) and (pointer: coarse)`):**
- All clickable elements get 44px tap targets (`padding-top: 11px; padding-bottom: 11px`)
- Table row hover effects removed (`background: inherit`) — confusing on touch

### 7.4 CSS Techniques Used

| CSS Feature | What it does | Where we use it |
|-------------|-------------|-----------------|
| `@media (max-width: ...)` | Applies rules only below a screen width | Two breakpoints: 900px, 480px |
| `grid-template-columns: repeat(auto-fit, minmax(..., 1fr))` | Auto-wraps items to next row when they don't fit | Dashboard stat cards |
| `flex-wrap: wrap` | Flex items wrap to next line | Filter bars, page headers |
| `transform: translateX()` | Slides sidebar off-screen without animating layout | Mobile sidebar toggle |
| `display: none/block` | Shows/hides elements | Login branding panel, hamburger, overlay |
| `[style*="grid-template-columns"]` | CSS selector targeting inline styles | Collapsing two-column forms |

---

## 8. Responsive UI — Complete Attribute Inventory

Every CSS property and HTML element that makes the system responsive:

### CSS Properties (25 items)

| # | Rule | File:Line | What it does |
|---|------|-----------|-------------|
| 1 | `.sidebar-toggle { display: none; }` | `style.css:763` | Hide hamburger on desktop |
| 2 | `.sidebar-overlay { display: none; }` | `style.css:784` | Hide dark backdrop on desktop |
| 3 | `.login-outer { ... }` | `style.css:798` | Login page wrapper class |
| 4 | `@media (max-width: 900px) { ... }` | `style.css:807-905` | Main responsive block |
| 5 | `.sidebar { transform: translateX(-100%); }` | `style.css:809` | Slide sidebar off-screen |
| 6 | `.sidebar.open { transform: translateX(0); }` | `style.css:814` | Slide sidebar back in |
| 7 | `.sidebar-overlay { display: block; }` | `style.css:817` | Show backdrop on mobile |
| 8 | `.sidebar-toggle { display: flex; }` | `style.css:825` | Show hamburger on mobile |
| 9 | `.main-wrap { margin-left: 0; }` | `style.css:830` | Remove sidebar margin |
| 10 | `.login-outer { flex-direction: column !important; }` | `style.css:835` | Stack login panels |
| 11 | `.login-outer > div:first-child { display: none !important; }` | `style.css:838` | Hide branding panel |
| 12 | `.login-outer > div:last-child { width: 100% !important; }` | `style.css:841` | Full-width login form |
| 13 | `[style*="grid-template-columns"][style*="px"] { grid-template-columns: 1fr !important; }` | `style.css:849` | Collapse two-column forms |
| 14 | `.stat-grid { grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); }` | `style.css:862` | Smaller stat cards |
| 15 | `.filter-group { min-width: 120px; }` | `style.css:868` | Narrower filters |
| 16 | `.page-header { flex-direction: column; }` | `style.css:873` | Stack page header |
| 17 | `.page-body { padding: 16px; }` | `style.css:883` | Reduce page padding |
| 18 | `.card-header-bar { flex-direction: column; }` | `style.css:891` | Stack card header |
| 19 | `@media (max-width: 480px) { ... }` | `style.css:910-941` | Small phone block |
| 20 | `.stat-grid { grid-template-columns: 1fr; }` | `style.css:910` | Single column stat cards |
| 21 | `.filter-group { min-width: 100%; }` | `style.css:914` | Full-width filters |
| 22 | `.btn { padding: 8px 12px; font-size: 13px; }` | `style.css:923` | Smaller buttons |
| 23 | `@media (hover: none) and (pointer: coarse) { ... }` | `style.css:946-962` | Touch optimisation |
| 24 | `.sidebar-link, .btn, .btn-logout { padding-top: 11px; padding-bottom: 11px; }` | `style.css:947` | 44px tap targets |
| 25 | `.data-table tbody tr:hover { background: inherit; }` | `style.css:958` | Remove hover on touch |

### HTML / JS Additions (4 items)

| # | Element | File:Line | What it does |
|---|---------|-----------|-------------|
| 26 | `<div id="sidebar-overlay" onclick="toggleSidebar()">` | `base.html:117` | Dark backdrop when sidebar is open on mobile |
| 27 | `<button class="sidebar-toggle" onclick="toggleSidebar()">☰</button>` | `base.html:125-127` | Hamburger button in topbar |
| 28 | `<script>function toggleSidebar() { ... }</script>` | `base.html:166-171` | JavaScript toggles sidebar open/close |
| 29 | `class="login-outer"` added to outer div | `login.html:5` | Enables login responsive rules |

### How to Completely Remove All Responsiveness

> Delete lines **760-962** from `static/css/style.css` (hamburger, overlay, login-outer, all `@media` blocks). Then delete lines **117, 125-127, and 166-171** from `templates/shared/base.html`. Remove `login-outer` from line 5 of `templates/authentication/login.html`. The system goes back to desktop-only.

---

## 9. Responsive UI — Panel Q&A

### Q1: "Is your system responsive or adaptive?"

**Answer:** "Both, but the proper term is **responsive**. Our stat cards use CSS Grid with `auto-fit` — they wrap fluidly as the screen narrows, which is responsive. The sidebar toggle switches at exactly 900px — that's adaptive. Most modern sites combine both approaches."

### Q2: "What CSS properties make your system responsive?"

**Answer:** "Three main technologies: (1) **Media queries** — `@media (max-width: 900px)` and `@media (max-width: 480px)` that trigger layout changes. (2) **CSS Grid with auto-fit** — `grid-template-columns: repeat(auto-fit, minmax(200px, 1fr))` which makes dashboard stat cards wrap naturally. (3) **Transform** — `transform: translateX(-100%)` to slide the sidebar off-screen on mobile without causing layout reflow."

### Q3: "Why did you choose 900px and 480px breakpoints?"

**Answer:** "900px catches iPad Mini (768px), iPad Air (820px), and all phones. The sidebar becomes a hamburger menu below this width. 480px targets small phones like iPhone SE (375px) — below this, stat cards become single column and fonts shrink slightly to fit the narrowest screens."

### Q4: "Why did you use `!important` in the CSS?"

**Answer:** "For the media query overrides that target **inline styles** — the two-column grids written directly in HTML templates. Inline styles have the highest CSS specificity and cannot be overridden without `!important`. In a production app, we would refactor these inline styles into proper CSS classes, but for this project `!important` was the pragmatic shortcut."

### Q5: "How did you test the responsive design?"

**Answer:** "Using Google Chrome's DevTools device emulation (Ctrl+Shift+M). We tested iPhone 14 Pro Max (430px), iPhone SE (375px — smallest), iPad Mini (768px), and iPad Pro (1024px — just above the breakpoint). We also verified touch behaviour using Chrome's touch emulation."
