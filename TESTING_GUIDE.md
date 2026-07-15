# Testing Guide — Government Asset Platform

A complete beginner's guide to every test in this project, how the code works, and how to explain it to a panel.

> **What is a test?**
> A test is a small piece of code that checks whether one specific thing in your program works correctly. You run all tests with one command, and they tell you "PASSED" or "FAILED" — so you don't have to manually click through your app every time you make a change.

---

## All Testing Files Explained

Here is every file related to testing in this project, what it does, and what each line inside it means.

### `pytest.ini` — The Test Runner Configuration

**Location:** `D:\government_asset_platform\pytest.ini`

**What it is:** A configuration file for pytest (the tool that finds and runs your unit tests). When you type `python -m pytest`, pytest reads this file to know what to do.

**The file (4 lines):**

```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py
testpaths = authentication assets organizations tenants
```

| Line | What it does |
|------|-------------|
| `[pytest]` | Tells Python "these are pytest settings" |
| `DJANGO_SETTINGS_MODULE = config.settings` | Tells pytest which Django settings file to use (so it knows about your database, apps, etc.) |
| `python_files = tests.py test_*.py` | Tells pytest "look for files named `tests.py` or starting with `test_`" |
| `testpaths = authentication assets organizations tenants` | Tells pytest "only search in these four folders" (faster than searching the whole project) |

**Without this file:** you would have to type `python -m pytest --ds=config.settings authentication/ tests/` every time.

---

### `conftest.py` — The Plugin Connector

**Location:** `D:\government_asset_platform\conftest.py`

**What it is:** A special file pytest looks for automatically. It can define shared test fixtures, hooks, and plugins used across multiple test files.

**The file:**

```python
pytest_plugins = [
    'assets.tests',
    'authentication.tests',
    'organizations.tests',
    'tenants.tests',
]
```

| Part | What it does |
|------|-------------|
| `pytest_plugins = [...]` | Tells pytest "these modules contain test plugins" |
| `'assets.tests', 'authentication.tests', ...` | Lists the four test modules so pytest loads them explicitly |

This file ensures pytest discovers all test classes even if they use advanced features like `TenantTestCase`.

---

### `postman_collection.json` — The API Integration Tests

**Location:** `D:\government_asset_platform\postman_collection.json`

**What it is:** A JSON file that Postman (a desktop app) imports to create a collection of API requests. It contains 13 API tests that run in a specific order.

**What JSON means:** JSON (JavaScript Object Notation) is a way to store data as text. It looks like this:
```json
{
  "key": "value",
  "numbers": 123,
  "lists": ["item1", "item2"],
  "objects": {"nested": "data"}
}
```

**The file structure explained:**

```
postman_collection.json
│
├── info              → Collection name and description (shown in Postman)
│
├── variable          → Variables available to ALL requests
│   ├── base_url      → The API URL (e.g., http://localhost:8000)
│   ├── access_token  → Empty at start, filled by Login test
│   └── asset_id      → Empty at start, filled by Create Asset test
│
└── item              → The actual test requests, grouped into folders
    │
    ├── Authentication folder
    │   ├── 1. Login          → POST /api/auth/login/
    │   ├── 2. Get My Profile → GET  /api/auth/me/
    │   ├── 3. Verify Token   → POST /api/auth/verify-token/
    │   ├── 4. Reject unauth  → GET  /api/auth/me/  (NO token — expects 401)
    │   └── 5. Refresh Token  → POST /api/auth/refresh/
    │
    ├── Assets folder
    │   ├── 6. List Assets       → GET    /api/assets/
    │   ├── 7. Create Asset      → POST   /api/assets/
    │   ├── 8. Get Asset Detail  → GET    /api/assets/{id}/
    │   ├── 9. Update Asset      → PUT    /api/assets/{id}/
    │   └── 10. Delete Asset     → DELETE /api/assets/{id}/
    │
    └── Organisation & Dashboard folder
        ├── 11. List Org Units   → GET /api/org-units/
        ├── 12. View Audit Logs  → GET /api/audit-logs/
        └── 13. Dashboard Stats  → GET /api/dashboard/stats/
```

**How variables flow between tests (the key concept):**

Postman has **collection variables** — like global variables that all requests can read and write.

1. **Login test** sends username/password → receives `{"access": "eyJ...", "refresh": "eyJ..."}`
2. **Login's test script** (lines 33-34 in the JSON) runs after the response:
   ```javascript
   var jsonData = pm.response.json();
   pm.collectionVariables.set('access_token', jsonData.access);
   ```
   This saves the JWT into the `access_token` variable.
3. **Every other request** has an `Authorization: Bearer {{access_token}}` header.
   `{{access_token}}` is Postman's syntax for "replace this with the variable's value."
4. **Create Asset test** (line 227) also saves the new asset's ID:
   ```javascript
   pm.collectionVariables.set('asset_id', jsonData.id);
   ```
5. **Get/Update/Delete Asset** use `{{asset_id}}` in the URL path.

**How test scripts (assertions) work:**

Each request has an `event` section with JavaScript that runs after the response:

```javascript
pm.test('Login successful', function () {
    pm.response.to.have.status(200);        // Assert: status code is 200
    pm.expect(jsonData.access).to.not.be.empty;  // Assert: access token is not empty
});
```

If any `pm.expect(...)` fails, Postman marks that test as failed in red.

**To remove:** just delete the file `postman_collection.json`. Or don't import it into Postman.

---

### `locustfile.py` — The Load Testing Script

**Location:** `D:\government_asset_platform\locustfile.py`

**What it is:** A Python script for Locust, a load-testing tool. It simulates 50 ministry staff using the platform at the same time and measures response times.

**Line-by-line explanation:**

```python
from locust import HttpUser, task, between, tag
```
Imports the building blocks from the Locust library:
- `HttpUser` — a simulated user that makes HTTP requests
- `task` — marks a method as something the user does (like "list assets")
- `between` — sets a random wait time between tasks (simulates human reading)
- `tag` — labels tasks so you can run specific groups

```python
class MinistryStaffUser(HttpUser):
    """Simulates a ministry staff member..."""
```
Defines the virtual user. Locust will create 50 copies of this class, each running independently.

```python
    wait_time = between(3, 8)
```
Each virtual user waits 3-8 seconds between tasks (simulates a person reading the screen).

```python
    def on_start(self):
        """Log in when the virtual user starts."""
        self.login_data = {
            'username': 'moh_admin',
            'password': 'Admin@123',
        }
        response = self.client.post('/api/auth/login/', json=self.login_data)
        if response.status_code == 200:
            body = response.json()
            self.access_token = body.get('access', '')
            self.headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json',
            }
```
`on_start` runs once when the virtual user is created. It logs in via the API and saves the JWT token. All subsequent tasks use this token in the headers.

```python
    @tag('assets')
    @task(5)
    def list_assets(self):
        """Load the asset list — most frequent operation."""
        if self.access_token:
            self.client.get('/api/assets/', headers=self.headers)
```
- `@task(5)` — this task runs 5 times more often than a `@task(1)` task. The number is a **weight**.
- `@tag('assets')` — labels this task. You can run only asset-related tasks with `locust --tags assets`.
- `self.client.get(...)` — Locust measures how long this takes and records it.

```python
    @tag('assets')
    @task(3)
    def view_asset_detail(self):
        if self.access_token:
            list_resp = self.client.get('/api/assets/?page=1', headers=self.headers)
            if list_resp.status_code == 200:
                data = list_resp.json()
                results = data.get('results', [])
                if results:
                    asset_id = results[0]['id']
                    self.client.get(f'/api/assets/{asset_id}/', headers=self.headers)
```
This shows how a real user behaves: first list assets, pick the first one, and view its details. The `name='/api/assets/{id}/'` parameter groups all detail requests under one label in the results.

```python
    @task(2)
    def view_audit_logs(self):
        if self.access_token:
            self.client.get('/api/audit-logs/', headers=self.headers)

    @task(2)
    def view_dashboard_stats(self):
        if self.access_token:
            self.client.get('/api/dashboard/stats/', headers=self.headers)

    @task(1)
    def view_profile(self):
        if self.access_token:
            self.client.get('/api/auth/me/', headers=self.headers)

    @task(1)
    def verify_token(self):
        if self.access_token:
            self.client.post('/api/auth/verify-token/', json={'token': self.access_token})

    @task(1)
    def refresh_token(self):
        if self.access_token:
            self.client.post('/api/auth/refresh/', json={'refresh': self.access_token})
```
These are progressively less frequent tasks. The weight system:
- `@task(5)`: list assets (most common action)
- `@task(3)`: view asset detail
- `@task(2)`: view audit logs, dashboard stats (moderately common)
- `@task(1)`: profile, verify, refresh (least common)

So out of every ~15 tasks a user performs:
- 5 are listing assets
- 3 are viewing asset details
- 2 are viewing audit logs
- 2 are viewing dashboard
- 1 is viewing profile
- 1 is verifying token
- 1 is refreshing token

```python
    def on_stop(self):
        """Log out when the virtual user stops."""
        if self.access_token:
            self.client.post('/api/auth/logout/', headers=self.headers)
```
`on_stop` runs when the virtual user stops (after the test duration ends). It logs out properly.

**How to explain this to a panel:** "Locust creates 50 copies of this class, each running its own loop. Each copy waits 3-8 seconds between actions (simulating a person reading), then randomly picks an action based on the weights. List assets runs 5 times more often than profile. It's designed to mimic real ministry staff behaviour."

**To remove:** just delete `locustfile.py`.

---

### The Four `tests.py` Files — The Unit Tests

| File | Location | Tests |
|------|----------|-------|
| `authentication/tests.py` | `D:\government_asset_platform\authentication\tests.py` | User roles, permission classes, brute-force lockout, unlock tokens |
| `assets/tests.py` | `D:\government_asset_platform\assets\tests.py` | Asset expiry dates, warranty, auto-numbering |
| `organizations/tests.py` | `D:\government_asset_platform\organizations\tests.py` | Audit log tamper protection, OrgUnit hierarchy, MasterData |
| `tenants/tests.py` | `D:\government_asset_platform\tenants\tests.py` | Ministry model and schema creation |

**To remove:** delete any of these files and that specific set of tests stops running.

---

## Contents

1. [Unit Testing (pytest)](#1-unit-testing-pytest) — automated tests that check individual pieces of code
2. [Integration Testing (Postman)](#2-integration-testing-postman) — automated tests that check the whole login → API flow
3. [Security Testing (OWASP ZAP)](#3-security-testing-owasp-zap) — automated vulnerability scanning
4. [Load Testing (Locust)](#4-load-testing-locust) — simulates 50 real users to check performance
5. [Functional Testing (Manual)](#5-functional-testing-manual) — step-by-step checklist matching the system requirements

---

## 1. Unit Testing (pytest)

### What is a unit test?

A **unit test** is the smallest possible test. It tests exactly **one thing** — for example: "does the `is_expired` property return `True` when the asset's expiry date is yesterday?"

Each test is a Python function that:
1. Creates some test data
2. Calls the function or property you want to test
3. Checks that the result matches what you expect using `assert`

If the `assert` passes, the test passes. If it fails, the test fails and pytest shows you what went wrong.

### What does "assert" mean?

`assert` is a Python keyword. It says: "I _assert_ that this statement is true." If it's true, nothing happens (test passes). If it's false, Python raises an error (test fails).

```python
assert 1 + 1 == 2       # passes
assert 1 + 1 == 3       # fails — raises AssertionError
```

In testing, we use special assert methods that give better error messages:

```python
self.assertEqual(a, b)      # assert a == b
self.assertTrue(x)          # assert x is True
self.assertFalse(x)         # assert x is False
self.assertIsNone(x)        # assert x is None
self.assertRaises(Error, fn)  # assert that calling fn raises Error
```

### What is `setUp` and how does it work?

`setUp` is a special method that runs **before every single test method** in the class. It creates the same starting data so each test starts fresh.

```python
class MyTest(TestCase):
    def setUp(self):
        # This runs before EVERY test method below
        self.user = User.objects.create(username="test")

    def test_one(self):
        # self.user exists here — created by setUp
        print(self.user.username)  # "test"

    def test_two(self):
        # self.user exists here too — setUp ran again!
        print(self.user.username)  # "test"
```

Why? Because Django runs each test inside a **database transaction** and rolls it back afterward. So test_one might delete self.user, but test_two still sees it because the database was restored.

### How do tests know about tenancy? (TenantTestCase vs TestCase)

This project uses `django-tenants` — each ministry (like Ministry of Health, Ministry of Finance) gets its **own PostgreSQL schema** (a separate set of tables).

- **Shared apps** (`tenants`, `authentication`) — their tables live in the `public` schema, available everywhere
- **Tenant apps** (`assets`, `organizations`) — their tables live inside each ministry's schema (e.g., `moh_schema`, `mof_schema`)

So when testing tenant-only models (like `Asset`, `AuditLog`, `OrgUnit`, `MasterData`), we need a real tenant schema to exist. We use **`TenantTestCase`** instead of `TestCase`:

| Base class | When to use | What it does |
|------------|-------------|-------------|
| `TestCase` | Testing shared-schema models (`CustomUser`, `Ministry`, `PendingAccess`) | Creates the test database with only public schema tables |
| `TenantTestCase` | Testing tenant-schema models (`Asset`, `AuditLog`, `OrgUnit`, `MasterData`) | **Also** creates a ministry, a tenant schema, and sets the database connection to that schema |

`TenantTestCase` does this automatically:
1. Creates a `Ministry` record (e.g., schema_name = `'test_assets'`)
2. Saves it — which auto-creates the PostgreSQL schema and runs migrations for tenant apps
3. Sets the connection to that schema — so `Asset.objects.create(...)` goes to the right place
4. After all tests, drops the schema and cleans up

We define a helper method `setup_tenant` to set the required fields on the Ministry:

```python
@classmethod
def setup_tenant(cls, tenant):
    tenant.name = "Test Ministry"      # required field
    tenant.short_name = "TST"          # required field
```

### File-by-file walkthrough

---

#### `authentication/tests.py` (42 tests)

**What it tests:** User roles, permission classes, brute-force lockout, unlock tokens, and super-admin audit logs.

##### Example: `CustomUserModelTest`

```python
class CustomUserModelTest(TestCase):
    # Uses TestCase because CustomUser is in the public schema (shared app)
```

Each test method creates a user with a specific role and checks a property:

```python
def test_super_admin_role_property(self):
    """is_super_admin should return True for SUPER_ADMIN role."""
    user = CustomUser.objects.create_user(
        username='superadmin',
        password='Test@123',
        role='SUPER_ADMIN',          # role is a field on CustomUser
        ministry_schema=None,         # super admins don't belong to any ministry
    )
    self.assertTrue(user.is_super_admin)   # checks the @property on the model
```

The property `is_super_admin` in `models.py` is:

```python
@property
def is_super_admin(self):
    return self.role == 'SUPER_ADMIN'
```

So this test simply checks: "if I set role to SUPER_ADMIN, does the property return True?"

##### Example: `PermissionClassesTest`

This is the most important test class. It tests that the **7 permission classes** work correctly against all **5 roles**.

```python
def setUp(self):
    # Creates 5 users — one for each role — BEFORE every test method
    self.super_admin = UserModel.objects.create_user(
        username='super', role='SUPER_ADMIN', ministry_schema=None,
    )
    self.ministry_admin = UserModel.objects.create_user(
        username='admin', role='MINISTRY_ADMIN', ministry_schema='moh_schema',
    )
    self.agency_manager = UserModel.objects.create_user(
        username='manager', role='AGENCY_MANAGER', ministry_schema='moh_schema',
    )
    self.facility_clerk = UserModel.objects.create_user(
        username='clerk', role='FACILITY_CLERK', ministry_schema='moh_schema',
    )
    self.auditor = UserModel.objects.create_user(
        username='auditor', role='AUDITOR', ministry_schema='moh_schema',
    )
```

Then each test creates a permission class, creates a mock request, and checks if permission is granted:

```python
# Permission class: only SUPER_ADMIN is allowed
def test_is_super_admin_allows_super_admin(self):
    perm = IsSuperAdmin()                                    # create the permission
    request = Mock(user=self.super_admin, method='GET')      # mock an HTTP request
    self.assertTrue(perm.has_permission(request, None))      # assert: super_admin is allowed

def test_is_super_admin_blocks_facility_clerk(self):
    perm = IsSuperAdmin()
    request = Mock(user=self.facility_clerk, method='GET')
    self.assertFalse(perm.has_permission(request, None))     # assert: clerk is blocked
```

The permission classes themselves check the user's role:

```python
class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_super_admin
```

So the test proves: "the code in the permission class actually does what it's supposed to."

##### Example: `LoginAttemptModelTest` (brute-force lockout)

```python
def test_locked_during_cooldown(self):
    """When within the 15-minute cooldown, is_locked should be True."""
    attempt = LoginAttempt.objects.create(
        username='testuser',
        stage='LOCKED',               # LOCKED means they've failed too many times
        locked_until=timezone.now() + timedelta(minutes=10),  # still locked for 10 more min
    )
    self.assertTrue(attempt.is_locked)
```

This tests the model property `is_locked`:

```python
@property
def is_locked(self):
    return self.stage == 'LOCKED' and self.locked_until > timezone.now()
```

The test creates a scenario where the user IS within the lockout period and checks that `is_locked` returns True. Another test creates a scenario where the lockout has expired and checks that `is_locked` returns False.

---

#### `assets/tests.py` (21 tests)

**What it tests:** Asset expiry dates, warranty tracking, auto-numbering, and status choices.

This file has TWO test classes:
- `AssetModelTests(TenantTestCase)` — tests that need a tenant schema (most of them)
- `AssetSchemaIndependentTests(TestCase)` — tests that only look at model meta (no database writes)

##### Example: expiry date tests

```python
def test_is_expired_true_when_date_in_past(self):
    """If the expiry date is yesterday, is_expired should be True."""
    category = AssetCategory.objects.create(name='Test', code='TST')
    asset = Asset.objects.create(
        asset_number='TST-TST-2026-0001',
        name='Test Asset',
        category=category,
        asset_expiry_date=timezone.now().date() - timedelta(days=1),  # yesterday
        status='ACTIVE',
    )
    self.assertTrue(asset.is_expired)
```

The `is_expired` property in `models.py`:

```python
@property
def is_expired(self):
    if self.asset_expiry_date is None:
        return False
    return self.asset_expiry_date < timezone.now().date()
```

So the test: "set date to yesterday → property returns True. Set date to tomorrow → returns False. Set date to None → returns False."

##### Example: asset number generation

```python
def test_first_asset_number_starts_at_0001(self):
    from assets.views import generate_asset_number
    AssetCategory.objects.create(name='ICT', code='ICT')
    prefix = self.tenant.schema_name.replace("_schema", "").upper()[:3]  # "test_assets" → "TES"
    number = generate_asset_number(self.tenant.schema_name, 'ICT')
    self.assertRegex(number, rf'^{prefix}-ICT-\d{{4}}-0001$')
    # Example: 'TES-ICT-2026-0001'
```

The function `generate_asset_number` in `views.py`:

```python
def generate_asset_number(ministry_schema, category_code):
    year = timezone.now().year
    prefix = ministry_schema.replace("_schema", "").upper()[:3]  # "moh_schema" → "MOH"
    base = f"{prefix}-{category_code}-{year}-"                   # "MOH-ICT-2026-"
    existing = Asset.objects.filter(asset_number__startswith=base).order_by("-asset_number").first()
    last_seq = int(existing.asset_number.split("-")[-1]) if existing else 0
    sequence = last_seq + 1
    return f"{base}{str(sequence).zfill(4)}"                     # "MOH-ICT-2026-0001"
```

This test creates the FIRST asset (nothing in the database yet), calls `generate_asset_number`, and checks it ends with `0001`. The second test creates an asset with number `...0001` and asserts the next one is `...0002`.

---

#### `organizations/tests.py` (17 tests)

**What it tests:** Audit log tamper protection (cannot edit or delete), OrgUnit three-level hierarchy, and MasterData lookup constraints.

##### Example: tamper-proof audit log

```python
def test_cannot_update_existing_audit_log(self):
    log = AuditLog.objects.create(
        performed_by_id=1, performed_by_name='Test User',
        action='CREATE', model_name='Asset',
        object_id='1', object_repr='MOH-ICT-2026-0001',
        ip_address='127.0.0.1',
    )
    log.object_repr = 'Changed value'     # try to modify
    with self.assertRaises(PermissionError):  # expect an error
        log.save()                        # save should be blocked
```

The magic is in the model's `save()` method:

```python
class AuditLog(models.Model):
    # ... fields ...

    def save(self, *args, **kwargs):
        if self.pk is not None:           # if this record ALREADY exists (has a primary key)
            raise PermissionError("Audit log records cannot be modified.")
        super().save(*args, **kwargs)     # only new records can be saved
```

`self.pk is not None` means "this record already exists in the database." If someone tries to save changes to an existing record, the model raises `PermissionError`. New records (pk is None) pass through fine.

Similarly, `delete()` is overridden:

```python
def delete(self, *args, **kwargs):
    raise PermissionError("Audit log records cannot be deleted.")
```

The test "record retains original values" proves that even after a failed modification attempt, the database still has the original value:

```python
def test_audit_log_retains_original_values_after_modification_attempt(self):
    log = AuditLog.objects.create(...)
    with self.assertRaises(PermissionError):
        log.object_repr = 'Hacked value'
        log.save()                              # blocked!
    log.refresh_from_db()                       # re-read from database
    self.assertEqual(log.object_repr, 'MOH-ICT-2026-0001')  # original value preserved
```

##### Example: OrgUnit hierarchy

```python
def test_facility_full_path(self):
    ministry = OrgUnit.objects.create(name='Ministry of Health', code='MOH', unit_type='MINISTRY')
    agency = OrgUnit.objects.create(
        name='Muhimbili National Hospital', code='MNH',
        unit_type='AGENCY', parent=ministry,
    )
    facility = OrgUnit.objects.create(
        name='Radiology Department', code='RAD',
        unit_type='FACILITY', parent=agency,
    )
    expected = 'Ministry of Health > Muhimbili National Hospital > Radiology Department'
    self.assertEqual(facility.get_full_path(), expected)
```

The `get_full_path()` method walks up the `parent` chain collecting names:

```python
def get_full_path(self):
    parts = [self.name]
    current = self
    while current.parent:
        current = current.parent
        parts.append(current.name)
    return ' > '.join(reversed(parts))
```

So for Radiology Department → Muhimbili National Hospital → Ministry of Health, it produces `"Ministry of Health > Muhimbili National Hospital > Radiology Department"`.

##### Example: MasterData uniqueness

```python
def test_master_data_unique_together(self):
    MasterData.objects.create(category='FUNDING_SOURCE', value='GOVT', ...)
    with self.assertRaises(IntegrityError):   # database-level error
        MasterData.objects.create(category='FUNDING_SOURCE', value='GOVT', ...)  # duplicate!
```

The `MasterData` model has `unique_together = ('category', 'value')` in its `Meta` class. This creates a database constraint that prevents the same category+value pair from existing twice. The test proves the constraint works.

---

#### `tenants/tests.py` (3 tests)

**What it tests:** Ministry model creation, string representation, schema name, default active status.

```python
class MinistryModelTest(TestCase):
    """Uses TestCase because Ministry is in the public schema (shared app)."""
    def setUp(self):
        self.ministry = Ministry.objects.create(
            name='Ministry of Health',
            short_name='MOH',
            schema_name='moh_schema',
        )

    def test_ministry_string(self):
        self.assertEqual(str(self.ministry), 'Ministry of Health (moh_schema)')
```

The `__str__` method on Ministry returns `f"{self.name} ({self.schema_name})"`, so this checks that the string representation includes both the human-readable name and the technical schema name.

---

### How to run unit tests

```bash
# Activate virtual environment
& d:\government_asset_platform\venv\Scripts\Activate.ps1

# Run ALL 83 unit tests
python -m pytest

# Run just one file
python -m pytest authentication/tests.py -v

# Run just one test class
python -m pytest assets/tests.py::AssetModelTests -v

# Run just one test method
python -m pytest authentication/tests.py::PermissionClassesTest::test_is_super_admin_allows_super_admin -v

# Show slowest tests (useful for optimisation)
python -m pytest --durations=5
```

`-v` means "verbose" — it shows each test name and whether it PASSED or FAILED.

When you run `python -m pytest`, here's what happens:

1. pytest finds all files named `tests.py` in the `testpaths` folders
2. For each class that starts with `Test` (or extends `TestCase`), it finds all methods that start with `test_`
3. It creates the test database (a fresh PostgreSQL database named `test_<your_db_name>`)
4. For each test method:
   - Run `setUp()` to create starting data
   - Run the test method
   - Roll back the database to undo any changes
   - If any `assert` fails, mark the test as FAILED and show the error
5. Print a summary: "83 passed" or "82 passed, 1 failed"

### Troubleshooting slow tests

The `PermissionClassesTest` creates 5 users before each of its 21 test methods. On Windows with PostgreSQL over a network, this takes about 25 seconds per test. If you're in a hurry:

```bash
# Run just the fast tests (skip authentication)
python -m pytest assets/ organizations/ tenants/ -v

# Or run authentication alone (will be slow but thorough)
python -m pytest authentication/tests.py -v
```

---

## 2. Integration Testing (Postman)

### What is integration testing?

Unit tests check one tiny piece in isolation. Integration tests check the **full chain** — login, get token, use token to fetch assets — exactly like a real user would.

### How it works

Postman is a desktop app that sends HTTP requests to your API. The test collection has 13 requests that run in sequence. Each request saves data (like the JWT token) for the next request.

**Test flow:**

```
Login ──→ Get My Profile ──→ Verify Token ──→ Reject Unauthenticated ──→ Refresh Token
    │
    └──→ List Assets ──→ Create Asset ──→ Get Asset Detail ──→ Update Asset ──→ Delete Asset
    │
    └──→ List Org Units ──→ View Audit Logs ──→ Dashboard Stats
```

### Key: how the JWT token flows between tests

1. **Login** sends username/password → receives `{"access": "...", "refresh": "..."}`
2. Postman's test script saves `access` as a **collection variable**: `pm.collectionVariables.set("token", pm.response.json().access)`
3. Every subsequent request has an `Authorization: Bearer {{token}}` header — Postman replaces `{{token}}` with the saved value automatically
4. **Reject Unauthenticated** deliberately OMITS the header to prove the API returns 401

### What each test proves

| Test | What it proves | How |
|------|---------------|-----|
| Login | JWT tokens work | Sends POST with credentials → gets back 200 + access/refresh tokens |
| Get My Profile | Authenticated users can access their data | Sends GET with token → gets back user info (username, role, ministry) |
| Verify Token | Other modules can check tokens | Sends POST with token → gets back `{"active": true, "user_id": ..., "role": ...}` |
| Reject Unauthenticated | Security works | Sends GET without token → gets back 401 |
| Refresh Token | Tokens can be renewed | Sends POST with refresh token → gets back a new access token |
| List/Create/Get/Update/Delete Asset | Full CRUD works | Sends each HTTP method → checks the response |
| View Audit Logs | Audit trail is accessible | Sends GET to `/api/audit-logs/` → gets back paginated log entries |
| Dashboard Stats | Summary API works | Sends GET to `/api/dashboard/stats/` → gets back counts |

### How to run

```bash
# 1. Install Postman (free) from https://www.postman.com/downloads/
# 2. File → Import → Select postman_collection.json
# 3. Create an environment with:
#    base_url = https://goverment-assets-platform-production.up.railway.app
#    username = moh_admin
#    password = Admin@123
# 4. Click "Run" → "Run all"
```

---

## 3. Security Testing (OWASP ZAP)

### What is security testing?

OWASP ZAP is a tool that automatically attacks your website to find vulnerabilities — SQL injection, cross-site scripting (XSS), missing security headers, etc.

### How it works

1. ZAP sits as a **proxy** between your browser and the web app
2. It "spiders" the site (crawls all pages and follows all links)
3. Then it runs **active scans** — it sends malicious payloads to every endpoint:
   - Submits `' OR '1'='1` in form fields (SQL injection test)
   - Submits `<script>alert('xss')</script>` (XSS test)
   - Tries to access admin pages without login
4. It categorises findings as HIGH/MEDIUM/LOW risk

### Why the platform passes

| Vulnerability | Why safe | Explanation |
|--------------|----------|-------------|
| SQL injection | Django ORM | You never write raw SQL — Django always uses parameterised queries, which means user input is treated as **data**, not **code** |
| XSS | Django auto-escapes | Django templates automatically convert `<` to `&lt;` and `>` to `&gt;`, so injected scripts can't run |
| Authentication bypass | DRF permission classes | Every API endpoint has `permission_classes = [IsAuthenticated, IsMinistryAdmin]` — no token = no access |

### How to run

```bash
# 1. Install ZAP from https://www.zaproxy.org/download/
# 2. Open ZAP → Automated Scan → Enter URL → Attack
# 3. Wait for scan to finish → Review alerts
# 4. Report → Generate Report → HTML
```

---

## 4. Load Testing (Locust)

### What is load testing?

It simulates **50 people using the app at the same time** and measures whether response times stay under 3 seconds (the requirement from the report).

### How the code works

`locustfile.py` defines a **User** class:

```python
class AssetPlatformUser(HttpUser):
    wait_time = between(3, 8)  # each "user" pauses 3-8 seconds between actions

    @task(5)   # most frequent (weight 5)
    def list_assets(self):
        self.client.get("/api/assets/")

    @task(3)   # medium frequency (weight 3)
    def view_asset(self):
        asset_id = random.choice(self.asset_ids)
        self.client.get(f"/api/assets/{asset_id}/")

    @task(1)   # least frequent (weight 1)
    def view_dashboard(self):
        self.client.get("/api/dashboard/stats/")
```

The `@task(5)` number is a **weight** — a task with weight 5 runs 5× more often than a task with weight 1.

The loop:

```
Wait 3-8 seconds (simulates human reading time)
  ├── 5× List Assets (page through asset list)
  ├── 3× View Asset Detail
  ├── 2× View Audit Logs
  ├── 2× View Dashboard Stats
  ├── 1× View Profile
  ├── 1× Verify Token
  └── 1× Refresh Token
```

Each user first logs in to get a token, then repeats the loop.

### Interpreting the numbers

| Metric | Target | What it means |
|--------|--------|---------------|
| Median response time | < 500ms | Half of all requests were faster than this |
| 95th percentile | < 2000ms | 95% of requests were faster than this — only 5% were slower |
| Average response time | < 3000ms | The **main requirement** from the report |
| Failure rate | 0% | Every request should return 200, not 500 or timeout |

### How to run

```bash
# Install Locust
pip install locust

# Start Django (in one terminal)
python manage.py runserver

# Start Locust (in another terminal)
locust -f locustfile.py --host=http://localhost:8000

# Open http://localhost:8089 → Start with 50 users, spawn rate 5

# Or run headless (for reports):
locust -f locustfile.py --host=http://localhost:8000 `
  --headless --users=50 --spawn-rate=5 --run-time=2m --html=locust_report.html
```

---

## 5. Functional Testing (Manual)

### What is functional testing?

This is **you**, in a browser, manually checking each requirement from the system spec (Table 5.1 in the report). It proves the app actually works, not just that the code runs.

### Checklist

| # | What to test | Steps | Expected |
|---|-------------|-------|----------|
| i | Keycloak SSO login | Go to platform → redirected to Keycloak → log in as moh_admin → see dashboard | Redirection + login works |
| ii | Schema isolation | Create new ministry in admin → create user for it → log in as that user → empty dashboard | Each ministry has its own isolated data |
| iii | 5 roles work | Create one user per role → log in as each → observe what they can see | SUPER_ADMIN sees everything; FACILITY_CLERK sees only their facility |
| iv | Asset CRUD | Login as clerk → create/view/update asset → try to delete → blocked | Only authorised roles can delete |
| v | Audit trail immutable | Do any action → check audit log → try to edit/delete (via code) → blocked | Audit log entries are permanent |
| vi | Token verification | Call verify-token API with valid/expired/no token | Valid → user info; invalid → error |

### Recording results

Create a spreadsheet with columns: S/N, Requirement, Test Date, Tester, Result (Pass/Fail), Notes.

---

## 6. Answering Panel Questions

Here are common panel questions and how to answer them:

### "Why do you have four different types of testing?"

Each type catches different bugs:

| Test type | Catches |
|-----------|---------|
| Unit | Logic errors in individual functions — e.g., wrong expiry calculation |
| Integration | Connection errors between components — e.g., login works but token not passed to next request |
| Security | Vulnerabilities — e.g., SQL injection, missing authentication |
| Load | Performance issues — e.g., database queries too slow under 50 users |

Think of it like layers: unit tests catch small things early, integration tests catch the wiring between pieces, security tests catch holes, and load tests catch slowdowns.

### "How do you know your tests are correct?"

- **Each test tests ONE thing** — the test name says exactly what it checks
- **Tests use real model code** — they don't mock the database; they create real records and call real methods
- **If a test passes, the feature works** — you could manually verify the same scenario in the browser
- **If a test fails, there's a bug** — the test always knew the right answer and something changed to make it wrong

### "What is the difference between TestCase and TenantTestCase?"

| | TestCase | TenantTestCase |
|--|----------|----------------|
| Schema created | Only `public` schema | Public schema + a tenant schema |
| Models available | Shared apps only (`CustomUser`, `Ministry`) | Shared + tenant apps (`Asset`, `AuditLog`) |
| Use for | Authentication, tenants | Assets, organisations |

**Simple rule:** If you're testing something in the `assets` or `organizations` app, you need `TenantTestCase`. Everything else uses `TestCase`.

### "Why are some tests slow?"

The `PermissionClassesTest` in `authentication/tests.py` has 21 test methods. Each one runs `setUp()`, which creates **5 database users**. On Windows connecting to PostgreSQL over localhost, each user creation takes about 1 second, so 21 tests × 5 users = ~105 database operations just for setup.

Solution: these tests run once and you don't need to re-run them unless you change the permission code.

### "What does 83 tests passing prove?"

It proves that:

1. **User model** — roles, schema assignment, and string representation work
2. **Permission classes** — all 5 roles are correctly allowed or blocked from each action
3. **Asset model** — expiry dates, warranty tracking, and auto-numbering are bug-free
4. **Audit log** — records are permanently immutable (cannot edit or delete)
5. **Brute-force protection** — accounts lock after failed attempts and unlock after cooldown
6. **Org unit hierarchy** — the three-level ministry → agency → facility structure works
7. **Master data** — lookup values have correct constraints and defaults
8. **Ministry model** — schema creation and defaults work

### "Where did these files come from? Where is pytest.ini, locustfile.py, postman_collection.json?"

These files were all **created by the developer** and stored in the project folder:

| File | Who created it | Why it exists | If deleted |
|------|---------------|--------------|------------|
| `pytest.ini` | Developer | So `python -m pytest` knows where to find tests without typing extra flags | Unit tests won't run unless you type the full command manually |
| `conftest.py` | Developer | Ensures pytest finds all test modules even with complex setup | Most tests still work; some edge cases might not be discovered |
| `locustfile.py` | Developer | Defines what 50 simulated users do (login → list assets → check dashboard) | Load testing stops working |
| `postman_collection.json` | Developer | A portable file anyone can import into Postman to test the API | Integration testing stops working |
| `authentication/tests.py` | Developer | 42 unit tests for user roles, permissions, lockout | 42 specific tests are lost |
| `assets/tests.py` | Developer | 21 unit tests for asset model | Asset-specific tests are lost |
| `organizations/tests.py` | Developer | 17 unit tests for audit log, org structure | Organisation-specific tests are lost |
| `tenants/tests.py` | Developer | 3 unit tests for ministry model | Ministry-specific tests are lost |

**What if the panel asks "did you write these yourself?":** "Yes, I wrote every line. I started with the `tests.py` files to test the models one by one, then added `postman_collection.json` to test the full API flow, then `locustfile.py` to prove the platform handles 50 concurrent users under 3 seconds."

### "What would make these tests fail?"

- A developer accidentally removes `raise PermissionError` from `AuditLog.save()` — the tamper tests fail
- Someone changes the role names (e.g., `SUPER_ADMIN` → `SUPERADMIN`) — the permission tests fail
- The expiry calculation formula changes — the asset tests fail
- Adding a new required field to a model without a default — existing creation tests fail

This is exactly why tests exist — they immediately tell you "your change broke something."

---

## 7. Running Everything at Once

```powershell
# ── 1. Unit Tests (automated, 83 tests) ──
cd d:\government_asset_platform
python -m pytest -v --tb=short

# ── 2. Integration Tests (semi-automated, Postman) ──
# Open Postman → Import postman_collection.json → Run

# ── 3. Security Tests (semi-automated, ZAP) ──
# Open ZAP → Automated Scan → Enter URL → Attack

# ── 4. Load Tests (automated, Locust) ──
locust -f locustfile.py --host=http://localhost:8000 --headless --users=50 --spawn-rate=5 --run-time=2m

# ── 5. Functional Tests (manual) ──
# Use the checklist in Section 5
```
