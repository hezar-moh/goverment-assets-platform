# GOVERNMENT ASSET PLATFORM — Deployment: Local & Railway

> **Purpose:** Everything about running the system locally on your laptop and deploying it to Railway cloud. Commands, environment variables, database access, troubleshooting.

---

## Table of Contents

- [1. Local Development — Starting Everything](#1-local-development--starting-everything)
- [2. Railway Components & Architecture](#2-railway-components--architecture)
- [3. Local vs Railway Comparison](#3-local-vs-railway-comparison)
- [4. Environment Variables — Complete Reference](#4-environment-variables--complete-reference)
- [5. Database Access (pgAdmin, Railway Dashboard, psql)](#5-database-access-pgadmin-railway-dashboard-psql)
- [6. Understanding the Two Ports (5432 vs 30290)](#6-understanding-the-two-ports-5432-vs-30290)
- [7. Deployment Workflow — git push → Railway Auto-Deploy](#7-deployment-workflow--git-push--railway-auto-deploy)
- [8. Troubleshooting Common Issues](#8-troubleshooting-common-issues)

---

## 1. Local Development — Starting Everything

### 1.1 Prerequisites

| Software | Where to find it | How to check it's running |
|----------|-----------------|---------------------------|
| PostgreSQL | Windows service `postgresql-x64-18` | `Get-Service postgresql*` |
| Python 3.x | Installed globally | `python --version` |
| Keycloak | `C:\keycloak\keycloak-26.6.2\bin` | Must start manually |
| Flutter (optional) | `C:\Users\Hemed\govasset_mobile` | Must start manually |

### 1.2 Startup Commands (In Order)

```powershell
# Terminal 1: Start Django
# Make sure you're in the project folder
cd D:\government_asset_platform
& .\venv\Scripts\Activate.ps1
python manage.py runserver 0.0.0.0:8000

# Terminal 2: Start Keycloak (separate window)
cd C:\keycloak\keycloak-26.6.2\bin
.\kc.bat start-dev --http-port=8180

# Terminal 3: Start Flutter (optional, for mobile testing)
cd C:\Users\Hemed\govasset_mobile
flutter run
```

### 1.3 When to Use Each `runserver` Mode

| Command | Who can connect | Use case |
|---------|----------------|----------|
| `python manage.py runserver` | Only your browser (localhost) | Quick dev testing |
| `python manage.py runserver 0.0.0.0:8000` | Any device on your network | Phone app testing via hotspot |

### 1.4 Finding Your IP Address

```powershell
ipconfig
# Look for "IPv4 Address" under your hotspot/WiFi adapter
# Example: 192.168.100.18
```

If your IP changes, update:
1. `C:\Users\Hemed\govasset_mobile\lib\config\api_config.dart` — change `serverIp`
2. Railway Django Variables tab → `ALLOWED_HOSTS` — add the new IP

### 1.5 Management Commands Reference

```powershell
# --- Everyday Commands ---
python manage.py runserver 0.0.0.0:8000     # Start development server
python manage.py setup_demo_data             # Reset seed demo data
python manage.py setup_demo_data --sync-keycloak  # Reset + sync Keycloak users
python manage.py sync_keycloak_attributes    # Fix missing role/ministry_schema on Keycloak users
python manage.py migrate                     # Apply database migrations
python manage.py migrate_schemas             # Apply migrations to ALL schemas (public + tenant)
python manage.py collectstatic --noinput     # Gather static files for production
python -m pytest                             # Run all 83 unit tests

# --- Admin Commands ---
python manage.py createsuperuser             # Create Django superuser (for admin panel)
python manage.py shell                       # Open Django interactive Python shell

# --- Maintenance Commands ---
python manage.py makemigrations              # Generate migration files after model changes
python manage.py check --deploy              # Check production readiness
```

---

## 2. Railway Components & Architecture

### 2.1 The Three Railway Services

```
                                  INTERNET
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌─────────────────┐    ┌──────────────────────┐    ┌─────────────────┐
│  Django Service │    │   PostgreSQL Service  │    │ Keycloak Service│
│  (Gunicorn)     │    │                      │    │                 │
│                 │    │  Internal port: 5432  │    │ Port: 8080      │
│  URL:           │    │  Public proxy:       │    │                 │
│  goverment-     │    │  tokaido.proxy.      │    │ URL:            │
│  assets-        │    │  rlwy.net:30290      │    │ keycloak-       │
│  platform-      │    │                      │    │ production-     │
│  production     │    │  Database: railway   │    │ 4f96.up.        │
│  .up.railway    │    │                      │    │ railway.app     │
│  .app           │    └──────────────────────┘    └─────────────────┘
│                 │              ▲                         ▲
│  Port: 8080     │              │                         │
└─────────────────┘              │                         │
        │                        │                         │
        │  DATABASE_URL          │  KC_DB_URL              │
        └────────────────────────┴─────────────────────────┘
```

### 2.2 How They Connect Internally

| From | To | How | Env var used |
|------|----|-----|-------------|
| Django | PostgreSQL | Internal Railway network (`containers-us-west-xxx.railway.app:5432`) | `DATABASE_URL` |
| Keycloak | PostgreSQL | Same internal network | `KC_DB_URL` |
| Django | Keycloak | Internal Railway network | `KEYCLOAK_SERVER_URL` |
| Django ↔ Internet | Railway reverse proxy | `https://your-app.up.railway.app` | Auto by Railway |

### 2.3 Railway Django Startup (vs Local)

| Aspect | Local (`runserver`) | Railway (`Gunicorn`) |
|--------|-------------------|---------------------|
| Server type | Django dev server (single process) | Gunicorn (multi-worker) |
| Startup command | `python manage.py runserver` | `gunicorn config.wsgi` (from `Procfile` or `[start]` in `railway.json`) |
| Static files | Django serves them automatically | WhiteNoise serves them |
| HTTPS | No (HTTP) | Yes (auto by Railway) |
| Auto-restart | No (manual restart) | Yes (on file changes or crash) |

---

## 3. Local vs Railway Comparison

| Aspect | Local Development | Railway Production |
|--------|------------------|-------------------|
| Django URL | `http://localhost:8000` | `https://goverment-assets-platform-production.up.railway.app` |
| Keycloak URL | `http://localhost:8180` | `https://keycloak-production-4f96.up.railway.app` |
| PostgreSQL | Windows service (port 5432) | Railway PostgreSQL service |
| Database name | `government_assets_db` | `railway` (check PGDATABASE) |
| How to start | Manual (3 terminals) | Auto-deploy from git push |
| Static files | Dev server serves them | WhiteNoise serves them |
| Env vars | `.env` file on disk | Railway Dashboard → Variables tab |
| HTTPS | No | Yes (automatic) |
| Cost | Free (your laptop) | Free tier (1GB RAM each) |
| Data persistence | Your local PG | Railway PG (separate service) |
| Port for pgAdmin | `localhost:5432` | `tokaido.proxy.rlwy.net:30290` |

---

## 4. Environment Variables — Complete Reference

### 4.1 PostgreSQL Variables (Auto-Created by Railway)

These belong to the PostgreSQL service itself. Railway creates them automatically when you add a PostgreSQL service. You DON'T create these.

| Variable | What it is | How to read it |
|----------|-----------|---------------|
| `DATABASE_URL` | Full connection string: `postgresql://user:pass@host:5432/dbname` | Click `*******` to reveal |
| `DATABASE_PUBLIC_URL` | Same as above via public proxy | Hidden |
| `PGHOST` | Internal hostname (e.g., `containers-us-west-xxx.railway.app`) | Hidden |
| `PGPORT` | Internal port — always `5432` | Usually visible |
| `PGUSER` | Database username (usually `postgres`) | Hidden |
| `PGPASSWORD` | Database password (auto-generated, long random string) | Hidden |
| `PGDATABASE` | Database name (usually `railway`) | Hidden |
| `POSTGRES_DB` | Same as PGDATABASE (redundant, kept for compat.) | Hidden |
| `POSTGRES_USER` | Same as PGUSER (redundant) | Hidden |
| `POSTGRES_PASSWORD` | Same as PGPASSWORD (redundant) | Hidden |
| `PGDATA` | Internal path for PostgreSQL data files | Hidden |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | Seconds Railway waits before deploying | Visible |
| `SSL_CERT_DAYS` | Days remaining on SSL certificate | Visible |

### 4.2 Django Service Variables (YOU Create)

Add these in Railway Dashboard → Django service → Variables tab:

| Variable | What it should be | Default (if not set) |
|----------|------------------|---------------------|
| `KEYCLOAK_SERVER_URL` | `https://keycloak-production-4f96.up.railway.app` | `http://localhost:8180` |
| `KEYCLOAK_ADMIN_USERNAME` | `superadmin` | `admin` |
| `KEYCLOAK_ADMIN_PASSWORD` | `Admin@123` | `admin123` |
| `PLATFORM_BASE_URL` | `https://goverment-assets-platform-production.up.railway.app` | `http://localhost:8000` |
| `ALLOWED_HOSTS` | `goverment-assets-platform-production.up.railway.app,localhost` | (empty) |

### 4.3 Keycloak Service Variables (YOU Create)

Add these in Railway Dashboard → Keycloak service → Variables tab:

| Variable | What it should be | Notes |
|----------|------------------|-------|
| `KC_DB` | `postgres` | Tells Keycloak to use PostgreSQL (not embedded H2) |
| `KC_DB_URL` | `jdbc:postgresql://containers-us-west-xxx.railway.app:5432/railway` | Use the PGHOST + PGDATABASE from PostgreSQL Variables tab |
| `KC_DB_USERNAME` | `postgres` | Same as PGUSER |
| `KC_DB_PASSWORD` | (the hidden PGPASSWORD value) | Copy from PostgreSQL Variables tab |
| `KC_HOSTNAME` | `keycloak-production-4f96.up.railway.app` | Keycloak's own public URL |
| `KEYCLOAK_ADMIN` | `superadmin` | Initial admin username for Keycloak |
| `KEYCLOAK_ADMIN_PASSWORD` | `Admin@123` | Initial admin password |
| `KC_PROXY` | `edge` | Makes Keycloak work behind Railway's reverse proxy |
| `JAVA_OPTS_APPEND` | `-Xmx256m -Xms128m` | Limits memory to 256MB (prevents 502 errors on free tier) |
| `KC_HTTP_PORT` | `8080` | Internal port Keycloak listens on |

---

## 5. Database Access (pgAdmin, Railway Dashboard, psql)

### 5.1 Three Ways to Access the Database

| Method | What it is | When to use |
|--------|-----------|-------------|
| **pgAdmin** | Desktop app with graphical interface | Browsing tables, running SQL queries, inspecting schemas |
| **Railway Dashboard** | Web-based viewer in Railway | Quick checks — "does data exist?" |
| **psql** | Command-line PostgreSQL client | Scripts, automation, advanced queries |

### 5.2 Connecting pgAdmin to Railway PostgreSQL

**Step 1: Find your connection info**

In Railway Dashboard → PostgreSQL service:
- **Variables tab:** Reveal `PGUSER`, `PGPASSWORD`, `PGDATABASE` (click `*******`)
- **Networking section:** Find public proxy (e.g., `tokaido.proxy.rlwy.net:30290`)

**Step 2: Fill in pgAdmin**

Right-click "Servers" → "Register" → "Server":

| Field | What to type |
|-------|-------------|
| **Name** | `Railway PostgreSQL` (anything you like) |
| **Host name/address** | `tokaido.proxy.rlwy.net` (from Networking section) |
| **Port** | `30290` — the PUBLIC port (NOT 5432) |
| **Maintenance database** | Leave blank, or type `railway` (the PGDATABASE value) |
| **Username** | The revealed PGUSER value |
| **Password** | The revealed PGPASSWORD value |
| **Save password?** | ✅ Check this (so you don't retype every time) |
| **Role** | Leave blank |
| **Service** | Leave blank |

**Step 3: Click Save**

You should now see all databases, schemas, and tables.

### 5.3 pgAdmin Field Explanations

| Field | Plain English explanation |
|-------|-------------------------|
| **Host** | The computer address where PostgreSQL lives |
| **Port** | Which door number to knock on |
| **Maintenance database** | pgAdmin needs to connect to SOMETHING first. This is the initial landing database. Like entering a building lobby before choosing which office to visit. |
| **Save password?** | If checked, pgAdmin remembers your password. Convenient. |
| **Role** | A special permission level you can switch to after connecting. 99% of people never use this. Leave blank. |
| **Service** | A shortcut name for a group of connection settings stored in a file. Leave blank. |

### 5.4 ⚠️ Important pgAdmin Note

In pgAdmin's **View/Edit Data** grid (right-click table → View/Edit Data), after you type or edit data in a cell, you MUST click the **lightning bolt button (⚡ Save Data Changes)** or press **F6**. Just clicking away from the cell does NOT save.

**Alternative:** Use the **Query Tool** (right-click table → Query Tool) and write raw SQL:
```sql
INSERT INTO table_name (col1, col2) VALUES ('val1', 'val2');
UPDATE table_name SET col1 = 'new_val' WHERE id = 1;
DELETE FROM table_name WHERE id = 1;
```
Then click the **⚡ Execute** button — this always commits immediately.

### 5.5 Checking Schemas (for django-tenants)

In pgAdmin: Expand Server → Databases → railway → Schemas

Or run this SQL:
```sql
SELECT schema_name FROM information_schema.schemata
WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast');
```

You should see:
- `public` — shared tables (users, ministries, domains)
- `moh_schema` — Ministry of Health data
- `mof_schema` — Ministry of Finance data

### 5.6 Dropping a Schema (Reset a Ministry)

```sql
DROP SCHEMA moh_schema CASCADE;
```

Or from Django shell:
```python
from tenants.models import Ministry
m = Ministry.objects.get(schema_name='moh_schema')
m.delete(force_drop=True)  # drops schema + all its data
```

### 5.7 Important: Changes Are Real-Time

- Add a user in Django admin → refresh pgAdmin → appears immediately
- Add data directly in pgAdmin → refresh Django website → appears immediately
- **It is the same database** — Django, Keycloak, and pgAdmin all connect to the same PostgreSQL

---

## 6. Understanding the Two Ports (5432 vs 30290)

### 6.1 Why Two Ports?

```
YOUR LAPTOP (pgAdmin)              RAILWAY INTERNAL
┌─────────────────────┐          ┌──────────────────────────┐
│ Connect to :30290    │          │  Django uses :5432       │
│ (tokaido public)    │─────────→│  Keycloak uses :5432     │
│                     │  forwards│  PostgreSQL lives on :5432│
└─────────────────────┘          └──────────────────────────┘
```

- **`:5432`** — PostgreSQL's real port. ONLY accessible inside Railway's internal network. Django and Keycloak use this because they live inside Railway.
- **`:30290`** — Railway's public proxy port. Forwards to the internal `:5432`. YOU use this from pgAdmin on your laptop.

### 6.2 The Analogy

Think of Railway PostgreSQL as a secure building:
- **`:5432`** is the **staff entrance** inside the building. Django and Keycloak use this because they're already inside.
- **`:30290`** is the **public reception desk**. You (pgAdmin) must use THIS entrance because you're outside the building.

### 6.3 Finding Your Public Port

In Railway Dashboard → PostgreSQL service → **Networking** section:
```
tokaido.proxy.rlwy.net:30290 → :5432
```

This reads: "any connection to `tokaido.proxy.rlwy.net` on port `30290` gets forwarded to PostgreSQL on internal port `5432`."

### 6.4 Connecting via psql (Command Line)

```powershell
psql -h tokaido.proxy.rlwy.net -p 30290 -U postgres -d railway
# Enter password when prompted (the revealed PGPASSWORD)
```

---

## 7. Deployment Workflow — git push → Railway Auto-Deploy

### 7.1 The Complete Flow

```
YOU                          GITHUB                     RAILWAY
  │                            │                          │
  │── git add . ──────────────→│                          │
  │── git commit -m "msg" ────→│                          │
  │── git push ───────────────→│                          │
  │                            │                          │
  │                            │── Webhook triggers ─────→│
  │                            │                          │
  │                            │                          │── Detect change
  │                            │                          │── Pull code from GitHub
  │                            │                          │── Build container
  │                            │                          │── Install dependencies
  │                            │                          │── Run collectstatic
  │                            │                          │── Run migrations
  │                            │                          │── Start Gunicorn
  │                            │                          │── Health check
  │                            │                          │── Route traffic to new
  │                            │                          │── Done ✓
  │                            │                          │
  │←── (1-2 minutes) ─────────│──────────────────────────│
```

### 7.2 What Stays vs What Changes

| Stays the same | Changes |
|----------------|---------|
| PostgreSQL data (separate service) | Django code gets updated |
| Keycloak data (same PostgreSQL) | Static files get rebuilt |
| Env vars (set in Dashboard) | Migrations run |
| User accounts, assets, audit logs | |

### 7.3 Deployment Safety

- Railway uses **draining** — waits for active requests to finish before switching
- PostgreSQL is a **separate service** — never goes down during Django deploys
- At worst: a user might see a brief 502 error for <30 seconds
- To roll back: `git revert` the last commit and push again

### 7.4 Checking Deployment Status

```
Railway Dashboard → Django service → Deployments tab
  → Click any deploy → View build logs
  → Look for: "Health check passed" or any error messages
```

---

## 8. Troubleshooting Common Issues

### 8.1 Keycloak Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| 403 on "Manage Account" page | Web Origins empty in `account-console` client | Add Django URL to Web Origins in account-console client |
| 502 errors on Railway Keycloak | Out of memory (free tier has 1GB) | Check `JAVA_OPTS_APPEND=-Xmx256m -Xms128m` is set |
| User created but can't log in | Missing `role`/`ministry_schema` attributes | Run `sync_keycloak_attributes` command |
| "User not found" after SSO login | User in Keycloak but NOT in Django | Approve PendingAccess or create user in Django admin |
| Admin API returns 401 | Wrong `KEYCLOAK_ADMIN_USERNAME`/`PASSWORD` | Set correct values in Railway Django Variables tab |
| Keycloak won't start on Railway | KC_DB_URL incorrect | Check PGHOST + PGDATABASE from PostgreSQL Variables |

### 8.2 Database Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Can't connect pgAdmin to Railway | Using wrong port | Use `30290` (public proxy), NOT `5432` |
| "could not connect to server" | PostgreSQL service not running | Check Railway Dashboard → PostgreSQL is green |
| Data appears in pgAdmin but not on website | Looking at wrong schema | Switch to correct schema in pgAdmin |
| Edit in pgAdmin not appearing on site | Didn't click Save Data Changes (F6) | Click ⚡ lightning bolt or press F6 |

### 8.3 Deployment Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Deploy fails | Syntax error or migration conflict | Check Railway deploy logs for details |
| Site works locally but not on Railway | Missing env vars | Compare Railway Variables with `.env` file |
| 500 error after deploy | Migration failed or missing dependency | Check Railway deploy logs |
| Static files not loading | collectstatic issue | WhiteNoise handles this — check settings.py |
| "Invalid HTTP_HOST" | IP not in ALLOWED_HOSTS | Add the IP to Railway Django Variables → `ALLOWED_HOSTS` |

### 8.4 Development Issues

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Phone can't reach Django | Django not on `0.0.0.0` | Run `python manage.py runserver 0.0.0.0:8000` |
| "Invalid HTTP_HOST" | IP not in ALLOWED_HOSTS | Add IP to settings.py or Railway Variables |
| Password not working | Keycloak not started | Run `kc.bat start-dev --http-port=8180` |
| Flutter can't connect | Wrong IP address | Run `ipconfig`, update `api_config.dart` |
| Django can't connect to PostgreSQL | PostgreSQL service stopped | Start PostgreSQL service: `Start-Service postgresql*` |
