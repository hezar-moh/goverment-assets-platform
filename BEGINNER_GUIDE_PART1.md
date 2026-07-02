# GOVERNMENT ASSET MANAGEMENT PLATFORM

# BEGINNER COMPLETE SYSTEM GUIDE — PART 1

## Chapters 1–6: Foundations

**Written for:** Someone who has never built a backend, API, or authentication system before.

**No prior knowledge assumed.** Everything explained from first principles.

**Running example throughout:** The GovAsset Platform at `D:\government_asset_platform`.

> **Chapters:** [1](#ch-1) · [2](#ch-2) · [2B](#ch-2b) · [3](#ch-3) · [4](#ch-4) · [5](#ch-5) · [6](#ch-6) · [7](#ch-7)

---


## HOW TO READ THIS GUIDE

Every chapter follows the same structure:

1. **EXPLAIN THE CONCEPT** — What is it? Simple analogy.
2. **WHY IT EXISTS** — What problem does it solve?
3. **WHAT HAPPENS WITHOUT IT** — The nightmare scenario.
4. **WHERE IT IS IN MY CODE** — Exact files, exact lines.
5. **HOW IT INTERACTS** — How it connects to everything else.
6. **ASCII DIAGRAM** — Visual picture.
7. **REAL GOVERNMENT EXAMPLE** — Using MOH, MOF, real people.
8. **PANEL QUESTION** — What you might be asked, with answer.
9. **BEGINNER MISCONCEPTION** — What people usually get wrong.

---

<a name="ch-1"></a>
## CHAPTER 1: WHAT IS THIS ENTIRE SYSTEM?


<a name="1-1"></a>
### 1.1 The One-Sentence Answer

> This is a **centralized digital record system** that lets multiple government ministries **track every physical item they own** — from laptops to ambulances to hospital beds — **securely online**, with **each ministry only seeing their own data**, accessible from **both a web browser and a mobile phone**.


<a name="1-2"></a>
### 1.2 The Real-World Problem

Before this system existed, here is how a government ministry tracked assets:

```
Ministry of Health owns 50,000+ items.
Tracked on: Paper notebooks, Excel files, sticky notes, memory.
When someone asks: "Where is the ultrasound machine we bought in 2022?"
Answer: Nobody knows. Maybe it's in storage. Maybe it's broken. 
Maybe someone took it home. No record exists.
```

**The audit problem:** At the end of the year, the government auditor comes to inspect. They ask: "Show me proof of purchase for these 500 items." If you cannot find the paper, or the Excel file got deleted, or someone wrote the wrong serial number, it is treated as **missing government property**. People can lose their jobs. Criminal charges can be filed.

**The maintenance problem:** A fire extinguisher needs to be replaced every 5 years. Without a system, nobody knows when the 5 years is up. The extinguisher stays on the wall, expired, and when a fire happens, it does not work. People die.

**The theft problem:** A laptop is assigned to an employee. The employee leaves the ministry. The laptop "disappears" — nobody knows to ask for it back. Over 10 years, hundreds of laptops vanish.


<a name="1-3"></a>
### 1.3 The Solution

This platform gives every ministry:

| Problem | Solution |
|---------|----------|
| Lost paper records | Digital database, backed up, searchable |
| Multiple Excel versions | One central system, everyone uses the same data |
| Expired equipment | Automatic expiry warnings (90 days, 30 days, expired) |
| Audit trail | Every action recorded, nobody can edit or delete |
| Theft | Asset assigned to specific location, tracked |
| Cross-ministry visibility | Each ministry sees only their own data |


<a name="1-4"></a>
### 1.4 Why Multiple Ministries Share One System

**Question:** Why not build a separate system for each ministry?

**Answer:** Because that would mean:

- 20 ministries × 20 separate servers = 20× the cost
- 20 separate databases to back up
- 20 separate user accounts for the same person
- 20 different login pages
- 20 different audit systems
- No single view for the government as a whole

Instead, we build **one platform** that serves **many ministries**. This is called **multi-tenancy**.

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ONE PLATFORM, ONE SERVER                          │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  MOH Schema   │  │  MOF Schema  │  │  MOE Schema  │    ...      │
│  │  (Health)     │  │  (Finance)   │  │  (Education) │              │
│  │               │  │              │  │              │              │
│  │  Assets       │  │  Assets      │  │  Assets      │              │
│  │  Org Units    │  │  Org Units   │  │  Org Units   │              │
│  │  Audit Log    │  │  Audit Log   │  │  Audit Log   │              │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘              │
│         │                 │                  │                       │
│         └─────────────────┼──────────────────┘                       │
│                           │                                          │
│                    ┌──────┴──────┐                                   │
│                    │  PostgreSQL  │                                   │
│                    │  Database    │                                   │
│                    └─────────────┘                                   │
└─────────────────────────────────────────────────────────────────────┘
```


<a name="1-5"></a>
### 1.5 The Users (5 Roles)

```
SUPER_ADMIN: Sees everything, manages ministries. 
             Works at central government level.
             
MINISTRY_ADMIN: Manages one ministry. Creates users, 
                manages assets, sees own ministry only.
                
AGENCY_MANAGER: Manages an agency under a ministry 
                (e.g., all hospitals under MOH).
                
FACILITY_CLERK: Manages one facility (e.g., one hospital).
                Can add/edit assets at their location.
                
AUDITOR: Read-only. Can see everything but cannot 
         change anything. For inspections.
```

**Real government example:**

```
Dr. Amina Hassan is the ICT Director at Ministry of Health.

She logs in as moh_admin (MINISTRY_ADMIN).
She can:
  - See all 9,472 assets belonging to MOH
  - Create new user accounts for hospital staff
  - Assign roles to staff
  - Edit asset records
  - Delete old disposed assets
  - View audit logs

She CANNOT see:
  - Any assets belonging to Ministry of Finance
  - Any users from Ministry of Finance
  - Platform-level settings

Mr. Juma Omary is the Super Admin at President's Office.
He can:
  - Add a new ministry to the platform
  - See statistics across ALL ministries
  - But he has NO personal assets
```


<a name="1-6"></a>
### 1.6 Three Ways to Access This System

```
┌─────────────────────────────────────────────────────────────────────┐
│                    THREE WAYS TO ACCESS                              │
│                                                                     │
│  WAY 1: Web Browser (HTML pages)                                    │
│  ┌────────────────────────────────────────────────────────┐        │
│  │  http://localhost:8000/dashboard/                       │        │
│  │  User logs in via Keycloak SSO                          │        │
│  │  Sees HTML tables, forms, buttons                       │        │
│  │  Full management interface                              │        │
│  └────────────────────────────────────────────────────────┘        │
│                                                                     │
│  WAY 2: Mobile App (Flutter)                                        │
│  ┌────────────────────────────────────────────────────────┐        │
│  │  Flutter app on Android phone                          │        │
│  │  Logs in via API (JWT token)                           │        │
│  │  Sees mobile-optimized UI                              │        │
│  │  Asset list, details, quick actions                    │        │
│  └────────────────────────────────────────────────────────┘        │
│                                                                     │
│  WAY 3: Other Government Systems (API)                              │
│  ┌────────────────────────────────────────────────────────┐        │
│  │  Ministry of Finance budgeting system                   │        │
│  │  Connects via API for data                              │        │
│  │  No user interface — machine-to-machine                 │        │
│  └────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────┘
```


<a name="1-7"></a>
### 1.7 Panel Questions for Chapter 1

**Q: Why did you build this system?**
A: To solve the problem of lost government assets. Before, tracking was paper-based — records were lost, expired equipment stayed in use, and auditors could not verify inventory. This system provides a digital, searchable, tamper-proof record of every government asset from purchase to disposal.

**Q: Why one platform instead of separate systems per ministry?**
A: Cost, maintenance, and interoperability. One platform costs a fraction of 20 separate systems. It also means a single audit system, a single SSO login, and the ability for future cross-ministry reporting. The multi-tenant architecture (django-tenants) keeps each ministry's data isolated while sharing the same code and server.

**Q: How do you keep ministries from seeing each other's data?**
A: Two layers: (1) At the application level — roles and permissions control what users see. (2) At the database level — each ministry's data lives in its own PostgreSQL schema. Even if a bug in our code allowed it, the database itself would refuse to return another ministry's data.

**Q: How many users can this support?**
A: The architecture supports hundreds of ministries and thousands of users. PostgreSQL handles billions of rows. Django can scale horizontally with Gunicorn workers. The main limit is server memory and disk space.

**Q: What if a new ministry needs to join?**
A: The Super Admin goes to /ministries/create/, fills in the ministry name and schema name, clicks save. Django automatically creates the new database schema, runs migrations, and creates the domain record. The ministry is live in under a minute.


<a name="1-8"></a>
### 1.8 Beginner Misconceptions

**Misconception:** "Each ministry needs their own server."
**Truth:** One server serves all ministries. The database separates their data using schemas. This is cheaper, easier to maintain, and provides centralized reporting.

**Misconception:** "If I can log into the website, I can see everything."
**Truth:** Your role determines what you see. A Facility Clerk at one hospital cannot even see another hospital's assets within the same ministry.

**Misconception:** "The mobile app is a separate system."
**Truth:** The mobile app uses the same server, same database, same authentication. It is just a different way of accessing the same data — through the API instead of web pages.

**Misconception:** "This is just an inventory app."
**Truth:** It is an asset LIFECYCLE management system. It tracks the full journey: planned → acquired → active → maintenance → disposed. With expiry warnings, audit trails, and multi-tenant isolation.

---

<a name="ch-2"></a>
## CHAPTER 2: WHAT IS A SERVER?


<a name="2-1"></a>
### 2.1 The Core Concept

**A server is just a computer that sits in a room (or a data center) and waits for requests.**

Your laptop is a computer you actively use. A server is a computer that sits quietly and does what other computers tell it to do.

```
YOUR LAPTOP (client)                THE SERVER (waiter)
┌───────────────────┐              ┌───────────────────┐
│ You type a URL    │  ──request──→│ Django receives it│
│                   │              │                   │
│ Browser shows page│  ←─response──│ Queries database  │
└───────────────────┘              │ Builds HTML page  │
                                   └───────────────────┘
```

**Think of it like a restaurant:**
- You = the **client** (customer)
- The waiter = the **server**
- The kitchen = the **database**
- The menu = the **website**

You tell the waiter what you want (request). The waiter goes to the kitchen (database), gets your food (data), and brings it back (response).


<a name="2-2"></a>
### 2.2 Where Everything Lives in Our Project

Our project has FOUR separate software systems running:

```
┌─────────────────────────────────────────────────────────────────┐
│                     YOUR LAPTOP (192.168.100.18)                 │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │ DJANGO (Port 8000)│  │ KEYCLOAK (8180)  │                     │
│  │                  │  │                   │                     │
│  │ python manage.py  │  │ kc.bat start-dev │                     │
│  │ runserver         │  │                   │                     │
│  │                  │  │  ┌─────────────┐  │                     │
│  │  ┌────────────┐  │  │  │ Keycloak    │  │                     │
│  │  │ My Code    │  │  │  │ Realm:      │  │                     │
│  │  │ (Django)   │  │  │  │ govasset    │  │                     │
│  │  └────────────┘  │  │  └─────────────┘  │                     │
│  └──────────────────┘  └──────────────────┘                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐       │
│  │ POSTGRESQL (Port 5432) — Windows Service             │       │
│  │                                                      │       │
│  │  Database: government_assets_db                      │       │
│  │    ├── Schema: public (shared: users, ministries)    │       │
│  │    ├── Schema: moh_schema (MOH: assets, orgs, logs)  │       │
│  │    └── Schema: mof_schema (MOF: assets, orgs, logs)  │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘


YOUR PHONE (client)              BROWSER (another client)
┌───────────────────┐            ┌───────────────────┐
│ Flutter App       │            │ Chrome/Firefox     │
│                   │            │                    │
│ Calls API at      │            │ Visits             │
│ 192.168.100.18:   │            │ localhost:8000     │
│ 8000/api/assets/  │            │ /login/            │
└───────────────────┘            └───────────────────┘
```


<a name="2-3"></a>
### 2.3 Each Component Explained

**A) Django — The Main Server (the waiter)**

- **File:** `manage.py` in `D:\government_asset_platform`
- **Command to start:** `python manage.py runserver 0.0.0.0:8000`
- **What it does:** Runs our Python code. Listens for HTTP requests. Returns web pages (HTML) or API responses (JSON).
- **Think of it as:** The entire restaurant — the waiters, the managers, the cashiers. It handles everything.

**B) PostgreSQL — The Database (the kitchen)**

- **File:** No files we touch. It is a Windows service called `postgresql-x64-18`.
- **Command to check:** `Get-Service postgresql*`
- **What it does:** Stores ALL data permanently. Users, assets, audit logs, everything.

**C) Keycloak — The Security Guard (SSO)**

- **File:** None in our project. It is a separate Java program in `C:\keycloak\bin`.
- **Command to start:** `kc.bat start-dev --http-port=8180`
- **What it does:** Handles passwords for web login. Users type their password into Keycloak's page, NOT into Django's page.

**D) Flutter — The Mobile App (another customer)**

- **Folder:** `C:\Users\Hemed\govasset_mobile`
- **Command to run:** `flutter run`
- **What it does:** A phone app that talks to Django's API.


<a name="2-4"></a>
### 2.4 The Key Distinctions

| Term | What it means | In our project |
|------|---------------|----------------|
| **Server** | The physical/virtual computer | Your laptop running Django |
| **Backend** | The code that runs ON the server | Our Django Python code |
| **Frontend** | The visual part the user sees | The HTML templates, or the Flutter app |
| **Database** | Where data is stored permanently | PostgreSQL |

**Common misconceptions:**

```
WRONG: "Django is the backend."
RIGHT: Django is the FRAMEWORK. Our Python code IS the backend.

WRONG: "The database is in Django."
RIGHT: The database is a SEPARATE program (PostgreSQL). Django CONNECTS to it.

WRONG: "The API is a separate server."
RIGHT: The API runs on the same Django server. It is just different URLs.
       /assets/ → HTML page
       /api/assets/ → JSON data
```


<a name="2-5"></a>
### 2.5 How They All Start Up

```
Step 1: PostgreSQL — AUTOMATIC (Windows starts it for you)
        ↓ Already running, waiting on port 5432

Step 2: Django — YOU run this
        ↓ python manage.py runserver 0.0.0.0:8000
        ↓ Connects to PostgreSQL, loads settings, starts listening

Step 3: Keycloak — YOU run this (separate terminal)
        ↓ kc.bat start-dev --http-port=8180
        ↓ Starts its own database, listens on port 8180

Step 4: Flutter — YOU run this (third terminal)
        ↓ flutter run
        ↓ Builds app, installs on phone via USB
        ↓ App connects to Django at 192.168.100.18:8000
```

**Wrong order problems:**
- Django before PostgreSQL → Error: "could not connect to server"
- Flutter before Django → "connection refused" errors
- Browser before Keycloak → Keycloak login page is down


<a name="2-6"></a>
### 2.6 How the Phone and Laptop "Find" Each Other

```
Your phone is on your hotspot.
Your laptop is connected to your hotspot.
They are in the SAME WiFi network.

Your laptop's IP on that network: 192.168.100.18 (from ipconfig)

Flutter app is configured with:
  C:\Users\Hemed\govasset_mobile\lib\config\api_config.dart
  static const String serverIp = '192.168.100.18';

Phone sends request to: http://192.168.100.18:8000/api/auth/login/
Hotspot delivers it to your laptop.
Django receives it.
```

**The phone does NOT need internet.** The hotspot creates a private network between the two devices.


<a name="2-7"></a>
### 2.7 Panel Questions for Chapter 2

**Q: What is the difference between a server and a database?**
A: A server runs our code and handles requests. A database stores data persistently. Django is the server, PostgreSQL is the database. Django connects to PostgreSQL when it needs to read or write data.

**Q: Why do we run three separate programs?**
A: Separation of concerns. Django handles business logic. PostgreSQL handles data storage. Keycloak handles authentication. Each does one job well. If we put authentication inside Django, we would be responsible for storing passwords securely — which is easy to get wrong.

**Q: Does the user need internet to use this system?**
A: No. Everything runs locally on the laptop. The database, server, and Keycloak are all on the same machine. The phone connects through the laptop's hotspot. No internet required.

**Q: What is the difference between a client and a server?**
A: The client (browser or mobile app) makes requests. The server (Django) responds to requests. The client starts the conversation. The server waits and answers.


<a name="2-8"></a>
### 2.8 Beginner Misconceptions

**Misconception:** "The internet is required for everything."
**Truth:** This system runs entirely on your local network (hotspot). No internet needed. The hotspot creates a private WiFi network between your phone and laptop.

**Misconception:** "The database is inside Django."
**Truth:** PostgreSQL is a completely separate program. It runs as a Windows service. Django just connects to it. You could replace PostgreSQL with a different database without changing Django code (mostly).

**Misconception:** "Python runs all the time."
**Truth:** Python/Django only runs when you type `python manage.py runserver`. When you close the terminal, Django stops. PostgreSQL runs in the background as a Windows service, starting automatically with your computer.

---

<a name="ch-2b"></a>
## CHAPTER 2B: DOMAINS, IP ADDRESSES, AND WHAT `runserver` REALLY MEANS


<a name="2b-1"></a>
### 2B.1 The Problem: Your Laptop Has Many Names

Your laptop has multiple "names" and "addresses." Which one should you use? It depends on who is connecting.

```
YOUR LAPTOP HAS:

1. localhost  (the name your laptop calls itself)
2. 127.0.0.1  (the IP version of localhost)
3. 192.168.100.18  (your laptop's WiFi/hotspot IP address)
4. ::1  (IPv6 version of localhost)
```

**Why this matters:** When you type `python manage.py runserver`, Django only listens on `127.0.0.1:8000`. Your phone CANNOT reach this address because your phone is on a different network. You must tell Django to listen on ALL addresses.


<a name="2b-2"></a>
### 2B.2 What `python manage.py runserver` Actually Does

```
Command: python manage.py runserver

What Django does:
  - Listens on 127.0.0.1:8000 (localhost only)
  - This means: ONLY programs on this same laptop can connect
  - Browser on this laptop: ✓ works
  - Phone on hotspot: ✗ CANNOT connect

Why this is the default:
  For security. In development, you usually only want your
  own browser to access the server. But when you need the
  phone app to work, you must change this.
```

```
Command: python manage.py runserver 0.0.0.0:8000

What Django does:
  - Listens on 0.0.0.0:8000 (ALL network interfaces)
  - This means: ANY device that can reach your laptop can connect
  - Browser on this laptop: ✓ works
  - Phone on hotspot: ✓ works
  - Other laptop on same WiFi: ✓ works

Why this is needed for the phone:
  Your phone is not "localhost" on your laptop. Your phone
  needs to reach your laptop via its hotspot IP (192.168.100.18).
  For that to work, Django must listen on 0.0.0.0.
```


<a name="2b-3"></a>
### 2B.3 The Four Addresses Explained

```
┌─────────────────────────────────────────────────────────────────┐
│                    FOUR WAYS TO REACH DJANGO                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  localhost                                                       │
│    What: A name that always means "this computer"                │
│    IP:   127.0.0.1                                               │
│    Who can use: Only programs on this laptop                     │
│    Example URL: http://localhost:8000/assets/                    │
│    Used for: Your own browser testing                            │
│                                                                   │
│  127.0.0.1                                                       │
│    What: The IP version of "this computer"                       │
│    Same as: localhost                                            │
│    Example URL: http://127.0.0.1:8000/assets/                   │
│    Used for: Same as localhost                                   │
│                                                                   │
│  0.0.0.0                                                         │
│    What: "ALL network interfaces" — not a real address           │
│    Effect: Django listens on every address the laptop has        │
│    Used for: Making Django reachable from other devices          │
│    NOT a URL: You never type http://0.0.0.0:8000                │
│                                                                   │
│  192.168.100.18 (your hotspot IP)                                │
│    What: Your laptop's real address on the hotspot network       │
│    Who can use: Any device connected to your hotspot             │
│    Example URL: http://192.168.100.18:8000/api/assets/          │
│    Used for: Phone app connecting via API                        │
│    How to find: Run ipconfig, look for "IPv4 Address"            │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

**Why `0.0.0.0` is not a URL you type:**
- `0.0.0.0` is a COMMAND for Django: "listen everywhere"
- It is NOT a real address you can visit
- You visit `http://192.168.100.18:8000/` instead
- Django receives the request because it's listening on `0.0.0.0`


<a name="2b-4"></a>
### 2B.4 How Your Phone Finds Your Laptop

```
YOUR PHONE                          YOUR LAPTOP
┌────────────────────┐             ┌────────────────────┐
│ Flutter app needs  │             │ Django running on  │
│ to reach Django    │             │ 0.0.0.0:8000      │
│                    │             │                    │
│ Configured with:   │             │ Has IP:            │
│ serverIp =         │             │ 192.168.100.18     │
│ "192.168.100.18"   │             │                    │
│                    │             │ Also has:          │
│ Phone sends to:    │             │ localhost → 127.0.0.1│
│ http://192.168.    │             │ hotspot → 192.168..│
│ 100.18:8000/api/   │             │                    │
│ assets/            │             │ Django is listening│
│                    │             │ on ALL of these    │
│ Phone is on the    │             │ because we used    │
│ SAME hotspot WiFi  │             │ 0.0.0.0           │
│ as the laptop      │             │                    │
└────────────────────┘             └────────────────────┘
```

**Step by step:**
1. Your laptop is on your phone's hotspot WiFi
2. Hotspot gave your laptop the IP: 192.168.100.18
3. You typed: `python manage.py runserver 0.0.0.0:8000`
4. Django is now listening on ALL addresses
5. Your Flutter app has: `serverIp = '192.168.100.18'`
6. Phone sends: `http://192.168.100.18:8000/api/assets/`
7. Hotspot network delivers the request to your laptop
8. Django receives it and responds

**The phone does NOT need internet.** The hotspot creates a direct private WiFi link between the two devices.


<a name="2b-5"></a>
### 2B.5 What if the IP Changes?

Every time you reconnect to a hotspot, the IP can change. You must update:

```
1. Flutter config file:
   C:\Users\Hemed\govasset_mobile\lib\config\api_config.dart
   Line: static const String serverIp = '192.168.100.18';
   → Change to the NEW IP
   → Rebuild: flutter run

2. Django ALLOWED_HOSTS:
   File: config/settings.py
   → Add the NEW IP to the list
   → Restart Django

3. Database Domain record:
   → Register the NEW IP as a domain
   → So django-tenants can route correctly
```

**To find your current IP:**
```powershell
ipconfig
```
Look for "IPv4 Address" under your hotspot adapter.


<a name="2b-6"></a>
### 2B.6 Domains and Subdomains — What They Are

A **domain** is a human-readable name for a server. Instead of `192.168.100.18`, you use `govasset.go.tz`.

**In development**, we fake this with `localhost`:
```
moh.localhost    → routes to moh_schema
mof.localhost    → routes to mof_schema
localhost        → routes to public schema (Super Admin)
```

**In production**, you would have real domains:
```
govasset.go.tz          → The main website (public schema)
moh.govasset.go.tz      → Ministry of Health (moh_schema)
mof.govasset.go.tz      → Ministry of Finance (mof_schema)
api.govasset.go.tz      → API endpoint
```


<a name="2b-7"></a>
### 2B.7 How Domain-to-Ministry Routing Works

File: `tenants/models.py`

```python
class Domain(DomainMixin):
    domain = models.CharField(max_length=253)
    # When someone visits "moh.localhost:8000",
    # django-tenants looks up this Domain record
    # and finds: "this belongs to Ministry of Health (moh_schema)"
```

```
BROWSER: http://moh.localhost:8000/dashboard/

Step 1: Browser resolves moh.localhost → 127.0.0.1 (localhost)
        (This works because .localhost always points to your own computer)

Step 2: Django receives the request

Step 3: TenantMainMiddleware runs (first middleware)
        Reads the Host header: "moh.localhost:8000"
        Extracts: "moh.localhost"

Step 4: django-tenants looks up in Domain table:
        SELECT * FROM tenants_domain WHERE domain = 'moh.localhost'
        → Finds: tenant_id = 1 (Ministry of Health)

Step 5: django-tenants sets database search_path:
        SET search_path = moh_schema;
        Now ALL queries use moh_schema tables

Step 6: View runs, queries the database
        All queries go to moh_schema
```

**What happens for IP access (mobile app):**
```
The phone visits: http://192.168.100.18:8000/api/assets/

Step 1-2: Same as above

Step 3: TenantMainMiddleware reads Host: "192.168.100.18:8000"
        Looks up domain: "192.168.100.18"
        → NOT FOUND in Domain table

Step 4: SHOW_PUBLIC_IF_NO_TENANT_FOUND = True
        Falls back to public schema

Step 5: SchemaMiddleware sets request.schema_name from user's profile
        User's ministry_schema = "moh_schema"
        View uses: with schema_context("moh_schema"):
        Actually queries the correct schema
```

**Why we need BOTH domain-based routing AND user-based schema:**
- Domains tell django-tenants which schema to use BEFORE the user logs in
- After login, the user's profile tells us which schema to use
- For API (mobile), the domain is just an IP, so we rely on the user's profile


<a name="2b-8"></a>
### 2B.8 Creating Ministry Domains

When a Super Admin creates a ministry through the web interface (at `/ministries/create/`):

```python
# In tenants/views.py, ministry_create_view():
# 1. Create the Ministry (schema)
ministry = Ministry(schema_name='moh_schema', name='Ministry of Health')
ministry.save()  # Creates PostgreSQL schema

# 2. Create the Domain
Domain.objects.create(
    domain='moh.localhost',      # In dev: moh.localhost
    tenant=ministry,
    is_primary=True
)
```

**In development**, you can visit:
- `http://localhost:8000/` — Super Admin (public schema)
- `http://moh.localhost:8000/` — Ministry of Health
- `http://mof.localhost:8000/` — Ministry of Finance

**To test a ministry domain:**
Just type `moh.localhost:8000` in your browser. It works because `.localhost` always resolves to `127.0.0.1`. No DNS configuration needed.


<a name="2b-9"></a>
### 2B.9 Panel Questions for Chapter 2B

**Q: Why do we use `0.0.0.0:8000` instead of just `runserver`?**
A: `runserver` alone listens only on localhost (127.0.0.1). Your phone cannot reach that. `0.0.0.0:8000` tells Django to listen on ALL network interfaces, including the hotspot IP your phone can reach.

**Q: What is the difference between 127.0.0.1 and 0.0.0.0?**
A: 127.0.0.1 is a specific address that means "this computer only." 0.0.0.0 is a wildcard that means "every address on this computer." You visit 127.0.0.1 to reach yourself. You use 0.0.0.0 to let others reach you.

**Q: How do domains work in development vs production?**
A: In development, we use `.localhost` domains (moh.localhost) which always resolve to your own computer. In production, we would use real domains like moh.govasset.go.tz that require DNS configuration.

**Q: What happens if SHOW_PUBLIC_IF_NO_TENANT_FOUND is False?**
A: If someone visits an IP address that isn't registered as a domain, Django would return a 404 error. Setting it to True lets API calls (via IP) fall through to the public schema, where our SchemaMiddleware then switches to the user's correct schema.

**Q: How does django-tenants know which schema to use before login?**
A: It reads the domain from the Host header. For a visit to moh.localhost, it finds the Domain record and switches to moh_schema. For the login page itself, this works in the public schema.


<a name="2b-10"></a>
### 2B.10 Beginner Misconceptions

**Misconception:** "0.0.0.0 is an address I can visit."
**Truth:** 0.0.0.0 is a command meaning "listen everywhere." You cannot type http://0.0.0.0:8000 in a browser. You type http://192.168.100.18:8000 instead.

**Misconception:** "localhost and 127.0.0.1 are different."
**Truth:** They are the SAME thing. localhost is a name. 127.0.0.1 is the IP address that name points to. Your computer's hosts file maps localhost → 127.0.0.1.

**Misconception:** "Domains need internet."
**Truth:** .localhost domains work WITHOUT internet. They are reserved for local development. Real domains (.go.tz) need DNS servers and internet.

**Misconception:** "The IP address never changes."
**Truth:** Your hotspot IP changes every time you connect to a different network. You must check it with `ipconfig` and update the Flutter app and ALLOWED_HOSTS.

**Misconception:** "I need to buy a domain for development."
**Truth:** For development, use `localhost` or `.localhost` domains. They work immediately with no configuration. You only buy real domains for production.

---

<a name="ch-3"></a>
## CHAPTER 3: WHAT IS A WEBSITE?


<a name="3-1"></a>
### 3.1 The Core Concept

When you type a URL into a browser and press Enter, here is what actually happens:

```
YOU TYPE: http://localhost:8000/dashboard/

Step 1: Browser looks at the URL
        ┌──────────┬──────────┬───────┬────────────┐
        │ http://  │ localhost│ :8000 │ /dashboard/ │
        │ protocol │ address  │ port  │ path        │
        └──────────┴──────────┴───────┴────────────┘

Step 2: Browser finds the server
        localhost → your own computer (127.0.0.1)
        :8000 → Django is listening here

Step 3: Browser sends an HTTP request
        GET /dashboard/ HTTP/1.1
        Host: localhost:8000

Step 4: Django receives the request
        ↓ Checks: Is this user logged in?
        ↓ Reads URL patterns (config/urls.py)
        ↓ Finds: /dashboard/ → dashboard_view
        ↓ Runs: dashboard_view(request)
        ↓ Checks user's role → loads different data
        ↓ Queries database for statistics
        ↓ Renders HTML template (templates/dashboard/dashboard.html)
        ↓ Returns HTML string

Step 5: Browser receives the response
        HTTP/1.1 200 OK
        Content-Type: text/html
        
        <!DOCTYPE html>
        <html>
        <head><title>Dashboard</title></head>
        <body>
          <h1>Welcome, moh_admin</h1>
          <p>Total Assets: 9</p>
          <p>Expired Assets: 2</p>
        </body>
        </html>

Step 6: Browser renders the HTML
        Converts HTML tags into visual elements
        Loads CSS styles (static/css/style.css)
        Shows the page to the user
```


<a name="3-2"></a>
### 3.2 Visual Timeline

```
BROWSER                  DJANGO                     POSTGRESQL
   │                       │                            │
   │──GET /dashboard/─────→│                            │
   │                       │                            │
   │                       │──Check session/cookie─────→│
   │                       │←──User is authenticated───│
   │                       │                            │
   │                       │──SELECT COUNT(*) FROM      │
   │                       │  assets_asset WHERE        │
   │                       │  status='ACTIVE'──────────→│
   │                       │←──Returns: 9─────────────│
   │                       │                            │
   │                       │──SELECT * FROM             │
   │                       │  organizations_auditlog    │
   │                       │  ORDER BY timestamp DESC   │
   │                       │  LIMIT 5──────────────────→│
   │                       │←──Returns: 5 rows─────────│
   │                       │                            │
   │                       │  Render dashboard.html     │
   │                       │  with the data             │
   │                       │                            │
   │←──HTML page (200 OK)─│                            │
   │                       │                            │
   │  Browser shows the    │                            │
   │  dashboard page       │                            │
```


<a name="3-3"></a>
### 3.3 The Two Types of Response

**A) HTML — For web browsers**

Used by: `assets/views.py`, `authentication/views.py`, `dashboard_views.py`

```html
<table>
  <tr>
    <td>MOH-ICT-2025-0001</td>
    <td>Dell Latitude 5440</td>
    <td>ACTIVE</td>
  </tr>
</table>
```

The browser renders this as a visual table with borders, colors, fonts.

**B) JSON — For mobile apps and APIs**

Used by: `assets/api_views.py`, `authentication/api_views.py`

```json
{
  "count": 9,
  "results": [
    {
      "asset_number": "MOH-ICT-2025-0001",
      "name": "Dell Latitude 5440",
      "status": "ACTIVE"
    }
  ]
}
```

The Flutter app parses this JSON and displays it using its own visual components.


<a name="3-4"></a>
### 3.4 How URLs Map to Code

The file `config/urls.py` is the **master directory**. Every URL that comes into Django is looked up here:

```python
urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('assets/', asset_list_view, name='asset_list'),
    path('assets/<int:asset_id>/', asset_detail_view, name='asset_detail'),
    path('api/auth/login/', LoginAPIView.as_view(), name='api_login'),
    ...
]
```

**When a request comes for `/assets/42/`:**
1. Django checks `urls.py`
2. Matches pattern: `assets/<int:asset_id>/`
3. Extracts `asset_id = 42`
4. Calls `asset_detail_view(request, asset_id=42)`


<a name="3-5"></a>
### 3.5 Templates — How HTML Pages Are Built

Templates are HTML files with placeholders that get filled with data.

**Example — `templates/assets/asset_list.html`:**
```html
{% extends "shared/base.html" %}
{% block content %}
<h1>Assets ({{ page_obj.paginator.count }} total)</h1>

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

**How Django processes this:**
1. Read the template file from disk
2. Replace `{{ asset.name }}` with actual data from the database
3. Repeat the `<tr>` block for each asset (the `{% for %}` loop)
4. Wrap in the base layout (header, sidebar, footer from `base.html`)
5. Return the complete HTML string


<a name="3-6"></a>
### 3.6 Static Files — CSS

**CSS (`static/css/style.css`):** Controls the visual design — colors, fonts, spacing, layout. All HTML pages link to this same CSS file.


<a name="3-7"></a>
### 3.7 What Would Happen Without Each Piece

| Missing piece | What happens |
|---------------|--------------|
| No `urls.py` | Django receives request but doesn't know what code to run. Returns 404. |
| No template | View runs, query runs, but Django can't build HTML. Returns 500 error. |
| No CSS | HTML works but looks plain — black text on white, no layout. |
| No database | View can't load data. Returns 500 error. |
| No model | Database table doesn't exist. Query fails. Returns 500 error. |


<a name="3-8"></a>
### 3.8 Panel Questions for Chapter 3

**Q: What happens when I type a URL and press Enter?**
A: The browser sends an HTTP request to Django. Django checks the URL against its URL patterns to find the right view function. The view runs — it queries the database, processes data, and renders a template. Django sends the resulting HTML back to the browser, which displays it.

**Q: What is the difference between a URL and an endpoint?**
A: A URL is the full web address (`http://localhost:8000/assets/`). An endpoint is a specific URL pattern that leads to a specific function (the `asset_list_view` function for `/assets/`). All endpoints are URLs, but not all URLs are meaningful endpoints.

**Q: What is a 404 error?**
A: 404 means "Not Found." Django checked all URL patterns and none matched the requested URL. The page does not exist.

**Q: What is a 500 error?**
A: 500 means "Internal Server Error." Something broke in the code — a database connection failed, a file was missing, or there was a bug in the code.


<a name="3-9"></a>
### 3.9 Beginner Misconceptions

**Misconception:** "The browser loads a file directly from the laptop."
**Truth:** The browser sends an HTTP request. Django receives it, processes it, runs code, queries a database, and builds the HTML dynamically. It is not just loading a static file.

**Misconception:** "The URL is the file path on the server."
**Truth:** The URL is mapped to Python code. `/assets/` does not mean there is a folder called `assets` with a file called `index.html`. It means Django runs the `asset_list_view` function.

**Misconception:** "HTML is what the server stores."
**Truth:** The HTML is GENERATED on the fly. The template is stored, but the data that fills it comes from the database. Every time you refresh, the data might be different if something changed in the database.

---

<a name="ch-4"></a>
## CHAPTER 4: WHAT IS AN API?


<a name="4-1"></a>
### 4.1 The Core Concept

**API stands for Application Programming Interface.**

In simple terms: **An API is a way for one piece of software to talk to another piece of software.**

```
TWO PEOPLE TALKING:
Person A: "What assets do you have?"
Person B: "I have a Dell laptop and a Toyota Land Cruiser."

TWO PROGRAMS TALKING (API):
Flutter App: GET /api/assets/
Django:      {"results": [{"name": "Dell Laptop"}, {"name": "Toyota Land Cruiser"}]}
```

**Why APIs exist:** Web pages (HTML) are designed for humans to read. APIs (JSON) are designed for programs to read.


<a name="4-2"></a>
### 4.2 API vs. Website — The Difference

```
WEBSITE (browser):
┌──────────────────────┐
│  Asset List          │
│  ┌────────┬────────┐│
│  │ Number │ Name   ││
│  ├────────┼────────┤│
│  │ MOH-01 │ Laptop ││  ← Human sees this
│  │ MOH-02 │ Truck  ││
│  └────────┴────────┘│
└──────────────────────┘

API (mobile app):
{"count": 2, "results": [
    {"asset_number": "MOH-01", "name": "Laptop"},
    {"asset_number": "MOH-02", "name": "Truck"}
]}  ← Program sees this
```

The **same data**, just formatted differently. The website returns HTML with visual layout. The API returns JSON with pure data.


<a name="4-3"></a>
### 4.3 Why the Mobile App Uses the API

The Flutter app cannot load HTML pages — it is not a web browser. It needs raw data to display using its own visual components.

```
FLUTTER APP FLOW:

1. User taps "Login" button
2. Flutter sends: POST /api/auth/login/ {"username": "...", "password": "..."}
3. Django returns: {"access": "eyJ...", "user": {"role": "MINISTRY_ADMIN", ...}}
4. Flutter stores the token
5. Flutter sends: GET /api/assets/ (with token in header)
6. Django returns: {"count": 9, "results": [{...}, {...}]}
7. Flutter displays assets in a list using its own UI components
```

If the Flutter app tried to visit the HTML page at `/assets/`, it would get back HTML with `<table>` tags that it cannot render. That is why the API exists.


<a name="4-4"></a>
### 4.4 HTTP Methods

Every API request uses one of these methods:

| Method | What it means | In our project |
|--------|---------------|----------------|
| **GET** | "Give me data" (read) | `GET /api/assets/` — List assets |
| **POST** | "Create something new" | `POST /api/auth/login/` — Log in |
| **PUT** | "Replace something entirely" | `PUT /api/assets/42/` — Update asset |
| **DELETE** | "Delete something" | `DELETE /api/assets/42/` — Delete asset |

**Analogy — A library:**
```
GET    /books/           → "Show me all books"
GET    /books/42/        → "Show me book #42"
POST   /books/           → "Add a new book" (send book details in body)
PUT    /books/42/        → "Replace book #42 with this new version"
DELETE /books/42/        → "Remove book #42 from the library"
```


<a name="4-5"></a>
### 4.5 Every API Endpoint in Our Project

```
AUTHENTICATION:
  POST   /api/auth/login/         Log in, get JWT token     Anyone
  POST   /api/auth/refresh/       Refresh expired token     Anyone
  GET    /api/auth/me/            Get my profile            Logged in
  GET    /api/auth/verify-token/  Verify token for others   Logged in
  POST   /api/auth/logout/        Log out, blacklist token  Logged in

ASSETS:
  GET    /api/assets/             List assets (filtered)    Most roles
  POST   /api/assets/             Create new asset          Non-auditors
  GET    /api/assets/42/          Get one asset details     Most roles
  PUT    /api/assets/42/          Update an asset           Non-auditors
  DELETE /api/assets/42/          Delete an asset           Ministry Admin
  GET    /api/assets/categories/  List asset categories     Most roles

ORGANISATION:
  GET    /api/org-units/          Get org hierarchy         Most roles

AUDIT:
  GET    /api/audit-logs/         Get audit log entries     Auditors+

DASHBOARD:
  GET    /api/dashboard/stats/    Get dashboard stats       Logged in
```


<a name="4-6"></a>
### 4.6 How Our API Is Organized

File: `authentication/api_urls.py`

```python
urlpatterns = [
    path('auth/login/', LoginAPIView.as_view(), name='api_login'),
    path('auth/refresh/', RefreshTokenAPIView.as_view(), name='api_refresh'),
    path('auth/me/', MeAPIView.as_view(), name='api_me'),
    path('auth/verify-token/', VerifyTokenAPIView.as_view(), name='api_verify_token'),
    path('auth/logout/', LogoutAPIView.as_view(), name='api_logout'),
    path('assets/', AssetListCreateAPIView.as_view(), name='api_asset_list'),
    path('assets/<int:asset_id>/', AssetDetailAPIView.as_view(), name='api_asset_detail'),
    path('assets/categories/', AssetCategoryListAPIView.as_view(), name='api_asset_categories'),
    path('org-units/', OrgUnitListAPIView.as_view(), name='api_org_units'),
    path('audit-logs/', AuditLogListAPIView.as_view(), name='api_audit_logs'),
    path('dashboard/stats/', DashboardStatsAPIView.as_view(), name='api_dashboard_stats'),
]
```

And in `config/urls.py`, line 141:
```python
path('api/', include('authentication.api_urls')),
```


<a name="4-7"></a>
### 4.7 JSON — The Language APIs Speak

**JSON (JavaScript Object Notation)** is a way of writing data that both humans and computers can read.

```json
{
  "id": 1,
  "username": "moh_admin",
  "full_name": "Amina Hassan",
  "role": "MINISTRY_ADMIN",
  "ministry_schema": "moh_schema",
  "is_active": true
}
```

**Rules of JSON:**
- `{ }` surround one object (one "thing")
- `"key": "value"` — every field has a name and a value
- `" "` around strings (text)
- Numbers without quotes: `42`, `3.14`
- Booleans: `true` or `false` (no quotes)
- Arrays: `[ ]` for lists: `["a", "b", "c"]`
- Objects can be nested: `{"user": {"name": "Amina", "role": "ADMIN"}}`


<a name="4-8"></a>
### 4.8 REST — The Rules for Building APIs

**REST (Representational State Transfer)** is a set of conventions for how APIs should be designed.

```
1. Use nouns for URLs, not verbs:
   GOOD:  GET /api/assets/        (noun: "assets")
   BAD:   GET /api/get-assets/    (verb: "get")

2. Use HTTP methods to mean different things:
   GET    = read
   POST   = create
   PUT    = update/replace
   DELETE = delete

3. Use IDs for specific resources:
   GET    /api/assets/    = all assets
   GET    /api/assets/42/ = asset #42 specifically

4. Return status codes to indicate success/failure:
   200 = OK (success)
   201 = Created (success after POST)
   400 = Bad request (you sent wrong data)
   401 = Unauthorized (not logged in)
   403 = Forbidden (logged in but not allowed)
   404 = Not found (doesn't exist)
   429 = Too many requests (rate limited)
   500 = Server error (something broke)
```


<a name="4-9"></a>
### 4.9 How Our API Returns Data (Serializers)

File: `authentication/api_serializers.py`

A **serializer** converts Django model objects (Python objects) into JSON.

```
DATABASE ROW (PostgreSQL)      PYTHON OBJECT (Django)       JSON (API Response)
┌─────────────────────────┐  ┌──────────────────────┐   ┌──────────────────────────┐
│ id: 1                   │  │ asset.id = 1         │   │ {                        │
│ name: "Dell Laptop"     │→│ asset.name = "Dell"  │→ │   "id": 1,               │
│ status: "ACTIVE"        │  │ asset.status = ACTIVE│   │   "name": "Dell Laptop", │
│ category_id: 10         │  │ asset.category_id=10 │   │   "status": "ACTIVE"     │
└─────────────────────────┘  └──────────────────────┘   │ }                       │
                                                         └──────────────────────────┘
```


<a name="4-10"></a>
### 4.10 Real Government Example — Another Ministry Using Our API

**Scenario:** Ministry of Finance builds their own budgeting system. They want to know the total value of assets owned by each ministry.

```
MOF Developer reads our Swagger docs at:
  http://localhost:8000/api/docs/

They find the endpoint:
  GET /api/auth/verify-token/

They call our admin and ask for:
  - A service account username and password
  - The API URL (http://192.168.100.18:8000)

They write code:
  1. POST /api/auth/login/ with the service account credentials
  2. Get back a JWT token
  3. For each ministry user, call GET /api/auth/verify-token/
  4. Call GET /api/assets/ to get all assets
  5. Calculate total value from acquisition_cost field
  6. Display in their budgeting dashboard
```


<a name="4-11"></a>
### 4.11 Panel Questions for Chapter 4

**Q: What is the difference between an API and a website?**
A: A website returns HTML pages designed for humans to read in a browser. An API returns JSON data designed for other programs to process. Both run on the same server and use the same database.

**Q: Why not just use the website for everything?**
A: Because mobile apps and other government systems cannot render HTML. The Flutter app needs structured data (JSON) to build its own user interface.

**Q: What is REST?**
A: A set of conventions for designing APIs: use nouns for URLs, HTTP methods for actions, status codes for results.

**Q: What is a status code?**
A: A three-digit number that tells the client what happened. 200 = success, 401 = not authenticated, 404 = not found, 500 = server error.

**Q: What is a serializer?**
A: Code that converts database objects into JSON (or JSON back into database objects). It defines exactly which fields to include and how to format them.


<a name="4-12"></a>
### 4.12 Beginner Misconceptions

**Misconception:** "The API is a separate program from the website."
**Truth:** Both the website and the API run in the same Django server. They just serve different URLs and return different formats. The website returns HTML. The API returns JSON.

**Misconception:** "An API endpoint is the same as a web page URL."
**Truth:** They are both URLs, but they return different things. A web page URL returns HTML with visual layout. An API endpoint returns JSON data. The API is not meant to be opened in a browser.

**Misconception:** "JSON is a programming language."
**Truth:** JSON is a data format, like a structured way of writing text. It is not a language. It cannot run code or make decisions. It is just data.

---

<a name="ch-5"></a>
## CHAPTER 5: WHAT IS SWAGGER?


<a name="5-1"></a>
### 5.1 The Core Concept

**Swagger is an auto-generated documentation page for your API.**

Instead of writing documentation by hand (which gets outdated the moment you change code), Swagger reads your code and generates documentation automatically.

**Where to find it:** `http://localhost:8000/api/docs/`

```
┌────────────────────────────────────────────────────────────────┐
│                      Swagger UI                                 │
│                                                                │
│  GovAsset Platform API                                         │
│  REST API for the Government Asset Management Platform         │
│                                                                │
│  ┌─ How to authenticate ──────────────────────────────────┐    │
│  │ 1. Call POST /api/auth/login/ with username/password     │    │
│  │ 2. Copy the 'access' token                              │    │
│  │ 3. Click Authorize, enter: Bearer {token}              │    │
│  │ 4. All requests now include the token automatically     │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                │
│  ┌─ Authorize ───────────────┐                                 │
│  │ [Enter Bearer Token]      │                                 │
│  │ [Authorize] [Close]       │                                 │
│  └──────────────────────────┘                                 │
│                                                                │
│  ┌─ AUTH ──────────────────────────────────────────────────┐   │
│  │ POST /api/auth/login/    [Try it out]                    │   │
│  │ POST /api/auth/refresh/  [Try it out]                    │   │
│  │ GET  /api/auth/me/       [Try it out]                    │   │
│  │ POST /api/auth/logout/   [Try it out]                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌─ ASSETS ───────────────────────────────────────────────┐    │
│  │ GET  /api/assets/              [Try it out]             │   │
│  │ POST /api/assets/              [Try it out]             │   │
│  │ GET  /api/assets/{asset_id}/   [Try it out]             │   │
│  │ PUT  /api/assets/{asset_id}/   [Try it out]             │   │
│  │ DELETE /api/assets/{asset_id}/ [Try it out]             │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────┘
```


<a name="5-2"></a>
### 5.2 Why Swagger Exists

**Problem:** Other government groups need to connect to our API. They need to know what endpoints are available, what data to send, and what data they will get back.

**Without Swagger:** We would write a Word document. It would be outdated, hard to navigate, and extra work to maintain.

**With Swagger:** The documentation is auto-generated from the actual code — always up to date. It is interactive — you can "Try it out" right in the browser. Zero maintenance.


<a name="5-3"></a>
### 5.3 How It Works in Our Code

File: `config/urls.py`, lines 59-80:

```python
schema_view = get_schema_view(
    openapi.Info(
        title="GovAsset Platform API",
        default_version='v1',
        description="REST API for the Government Asset Management Platform...",
        contact=openapi.Contact(email="admin@platform.go.tz"),
    ),
    public=True,
)

urlpatterns = [
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('api/redoc/', schema_view.with_ui('redoc', cache_timeout=0)),
]
```

**How Swagger discovers our endpoints:**
1. Reads ALL URL patterns in the project
2. For each view class, reads the docstring and serializer
3. Reads the model to understand field types
4. Reads permission classes to know authentication needed
5. Builds an OpenAPI specification (JSON file describing entire API)
6. Displays in a visual UI


<a name="5-4"></a>
### 5.4 "Try It Out" — The Killer Feature

```
Example: Try It Out on POST /api/auth/login/

Request:
  {
    "username": "moh_admin",
    "password": "Admin@123"
  }

Response:
  {
    "access": "eyJhbGciOiJIUzI1NiIs...",
    "refresh": "eyJhbGciOiJIUzI1NiIs...",
    "user": {
      "id": 1,
      "username": "moh_admin",
      "role": "MINISTRY_ADMIN",
      "ministry_schema": "moh_schema"
    }
  }
```


<a name="5-5"></a>
### 5.5 Panel Questions for Chapter 5

**Q: What is Swagger?**
A: Swagger is an auto-generated documentation tool for APIs. It reads our code and creates an interactive documentation page at `/api/docs/` where developers can see every endpoint, its parameters, and even try it out directly in the browser.

**Q: How is Swagger different from Postman?**
A: Swagger is automated documentation generated from code. Postman is a manual testing tool where you build requests by hand. Swagger shows what the API does. Postman tests whether it works.

**Q: Does Swagger expose our API to security risks?**
A: Swagger shows the documentation, but it enforces the same authentication as the API itself. You cannot access protected endpoints without a valid token just because you are using Swagger.


<a name="5-6"></a>
### 5.6 Beginner Misconceptions

**Misconception:** "Swagger is a separate tool I need to install."
**Truth:** Swagger is built into our project through the `drf-yasg` package. It runs as part of Django. You just visit `/api/docs/` in your browser.

**Misconception:** "Swagger documentation needs to be written by hand."
**Truth:** Swagger reads your code — the URL patterns, serializers, models, docstrings — and generates documentation automatically. You maintain it by updating your code, not by editing documentation.

**Misconception:** "Swagger only shows GET endpoints."
**Truth:** Swagger shows ALL endpoints — POST, PUT, DELETE — and lets you try them all. It also shows request bodies, response formats, and status codes.

---

<a name="ch-6"></a>
## CHAPTER 6: HOW DOES ANOTHER GOVERNMENT ORGANIZATION CONNECT?


<a name="6-1"></a>
### 6.1 The Scenario

The Ministry of Finance has built their own budgeting system. They want to display asset values from our system in their dashboard.


<a name="6-2"></a>
### 6.2 The Step-by-Step Process

```
STEP 1: Contact
        MOF developer contacts our system administrator.
        "We want to integrate with the GovAsset platform."

STEP 2: Documentation
        We send them: http://192.168.100.18:8000/api/docs/
        They explore: POST /api/auth/login/
                      GET /api/auth/verify-token/
                      GET /api/assets/

STEP 3: Credentials
        We create a service account for them:
        - Go to Users page → Create User
        - Username: mof_budget_system
        - Role: AUDITOR (read-only)
        - Ministry schema: (blank — cross-ministry)

STEP 4: Testing
        They test in Swagger first:
        - Login with mof_budget_system credentials
        - Get token
        - Try GET /api/assets/ → verify data format

STEP 5: Integration
        They write code in their budgeting system:

        def get_asset_values():
            # Step 1: Login
            response = requests.post(
                "http://192.168.100.18:8000/api/auth/login/",
                json={"username": "mof_budget_system", "password": "..."}
            )
            token = response.json()["access"]

            # Step 2: Get assets
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(
                "http://192.168.100.18:8000/api/assets/",
                headers=headers
            )
            assets = response.json()["results"]

            # Step 3: Calculate total value
            total = sum(a["acquisition_cost"] or 0 for a in assets)
            return total
```


<a name="6-3"></a>
### 6.3 What Credentials They Receive

```
URL:    http://192.168.100.18:8000
API:    /api/docs/ (Swagger documentation)
Auth:   POST /api/auth/login/
Username: mof_budget_system
Password: M0f@Budg3t!2025
Token:   (generated on login, expires in 30 minutes)
```

**What the service account can do:** Login, read assets, read org units, read audit logs, verify tokens.

**What it CANNOT do:** Create/edit/delete assets, manage users, manage ministries, use web pages.


<a name="6-4"></a>
### 6.4 The Verify Token Endpoint

File: `authentication/api_views.py`, `VerifyTokenAPIView`

This is crucial for cross-system authentication:

```
MOF's System receives a JWT token from a user.
MOF calls: GET /api/auth/verify-token/ with Bearer token

Our response:
  {
    "valid": true,
    "user": {
      "id": 1,
      "username": "moh_admin",
      "role": "MINISTRY_ADMIN",
      "ministry_schema": "moh_schema",
      "ministry": "Ministry of Health"
    }
  }

MOF now knows: the token is valid, this user is from MOH,
               her role is MINISTRY_ADMIN.
```


<a name="6-5"></a>
### 6.5 Authentication Methods Compared

| Method | How It Works | Used By |
|--------|-------------|---------|
| **JWT Token** | Login with username/password, get token, use for 30 min | Mobile app, external systems |
| **SSO / Keycloak** | Redirect to Keycloak, log in, redirect back with session | Web browser users |
| **Service Account** | Special limited-permission account for machine-to-machine | Other government systems |


<a name="6-6"></a>
### 6.6 Panel Questions for Chapter 6

**Q: How would another ministry connect to your API?**
A: We create a service account with AUDITOR role (read-only). We provide the API URL, Swagger documentation, and credentials. They authenticate via `POST /api/auth/login/`, get a JWT token, and call endpoints. The `POST /api/auth/verify-token/` endpoint lets them validate our tokens in their own system.

**Q: Do external systems need Keycloak?**
A: No. External systems authenticate via the API using username/password, same as the mobile app. Keycloak is only for web browser SSO login.

**Q: Can external systems see data across all ministries?**
A: That depends on the service account's ministry_schema. An AUDITOR with no ministry_schema can see all ministries. A service account assigned to `moh_schema` can only see MOH data.

**Q: How do you prevent external systems from abusing the API?**
A: Through rate limiting (in production Nginx), short-lived tokens (30 min), and role-based permissions. A service account with AUDITOR role can only read data, not modify it.


<a name="6-7"></a>
### 6.7 Beginner Misconceptions

**Misconception:** "External systems need their own login page."
**Truth:** External systems authenticate programmatically — they send username/password in code, not through a browser login page. They never see a login form.

**Misconception:** "We need to open our database to other ministries."
**Truth:** Other ministries never access our database directly. They go through our API, which controls exactly what data they can see and enforces authentication and permissions.

**Misconception:** "If I give someone credentials, they can see everything."
**Truth:** Credentials are tied to a specific user account with specific role and ministry_schema. We control exactly what that account can access. A service account can be locked to read-only or to a single ministry.

---

<a name="ch-7"></a>
## CHAPTER 7: INTEGRATING OTHER GOVERNMENT SYSTEMS (FULL STEP-BY-STEP)


<a name="7-1"></a>
### 7.1 Why This Chapter Exists

Other government systems need to read (and sometimes write) asset data from our platform. This chapter provides the complete, step-by-step guide for how a government developer at another ministry would integrate with our API.

**Who this chapter is for:**
- Developers at other ministries connecting to our API
- Our own team setting up service accounts for external systems
- Anyone who needs to understand how machine-to-machine authentication works


<a name="7-2"></a>
### 7.2 The Big Picture

```
OTHER GOV SYSTEM                       OUR GOVASSET PLATFORM
(Youth Ministry)                       (Health Ministry)

┌──────────────────┐                  ┌──────────────────────┐
│ Their App/System  │                  │ Django REST API       │
│                    │                  │                       │
│ 1. POST /api/auth │                  │ 2. Verify credentials │
│    /login/        │ ─── creds ──►    │ 3. Return JWT token   │
│                    │                  │                       │
│ 4. Store JWT       │ ◀── token ──── │ 5. Token expires in   │
│    (30 min)       │                  │    30 minutes         │
│                    │                  │                       │
│ 6. GET /api/assets │ ─── JWT ────►  │ 7. Verify JWT          │
│    /?page=1        │                  │ 8. Check permissions  │
│                    │                  │ 9. Query database     │
│ 10. Receive JSON  │ ◀── data ──── │ 10. Return results     │
│                    │                  │                       │
│ 11. Display assets │                  │                       │
│ in their own UI    │                  │                       │
└──────────────────┘                  └──────────────────────┘
```


<a name="7-3"></a>
### 7.3 Prerequisites (What the Other System Needs)

```
BEFORE STARTING, THE OTHER SYSTEM MUST HAVE:

□ A service account created by our Super Admin
  - Username: youth_ministry_api
  - Password: [generated, stored securely]
  - Role: AUDITOR (read-only) or MANAGER (can create/edit)
  - ministry_schema: "" (null, to see all ministries)
    OR "moh_schema" (to see only MOH data)

□ The API base URL
  - Dev: http://192.168.100.18:8000/api/
  - Prod: https://api.govasset.go.tz/api/

□ Access to Swagger documentation
  - Dev: http://192.168.100.18:8000/api/docs/
  - Prod: https://api.govasset.go.tz/api/docs/

□ A way to make HTTPS requests
  - Python: requests library
  - PHP: cURL
  - .NET: HttpClient
  - Java: OkHttp, RestTemplate
  - Node.js: axios, node-fetch
```


<a name="7-4"></a>
### 7.4 Step 1: Create the Service Account

Our Super Admin logs into the web interface and creates a service account:

```python
# In admin panel or via management command:
User.objects.create_user(
    username='youth_ministry_api',
    password='G3n3rated!Str0ng#P@ss2024',
    role='AUDITOR',
    ministry_schema='',  # null = all ministries
    is_service_account=True
)
```

**Key facts about service accounts:**
- `is_service_account=True`: This user cannot log in via browser (no web access)
- `role='AUDITOR'`: Read-only permissions. Cannot create, edit, or delete assets
- `ministry_schema=''`: Can see data from ALL ministries (global auditor)
- Password is auto-generated and shown once. Store in a password manager


<a name="7-5"></a>
### 7.5 Step 2: Authenticate and Get a Token

The external system sends a POST request to our login endpoint:

**Request:**
```
POST http://192.168.100.18:8000/api/auth/login/
Content-Type: application/json

{
    "username": "youth_ministry_api",
    "password": "G3n3rated!Str0ng#P@ss2024"
}
```

**Response (success):**
```json
{
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Python example (using requests library):**

```python
import requests

BASE_URL = "http://192.168.100.18:8000/api"

# Step 1: Login
login_response = requests.post(f"{BASE_URL}/auth/login/", json={
    "username": "youth_ministry_api",
    "password": "G3n3rated!Str0ng#P@ss2024"
})

access_token = login_response.json()["access"]
# Token expires in 30 minutes
```

**Node.js example:**

```javascript
const axios = require('axios');

const BASE_URL = 'http://192.168.100.18:8000/api';

// Step 1: Login
const loginResponse = await axios.post(`${BASE_URL}/auth/login/`, {
  username: 'youth_ministry_api',
  password: 'G3n3rated!Str0ng#P@ss2024'
});

const accessToken = loginResponse.data.access;
```


<a name="7-6"></a>
### 7.6 Step 3: Use the Token for API Calls

Every subsequent request includes the JWT token in the Authorization header:

**Request:**
```
GET http://192.168.100.18:8000/api/assets/?page=1&page_size=20
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
    "count": 2450,
    "next": "http://192.168.100.18:8000/api/assets/?page=2&page_size=20",
    "previous": null,
    "results": [
        {
            "id": 1,
            "asset_code": "MOH-AMB-001",
            "asset_name": "Toyota Land Cruiser Ambulance",
            "category": "Vehicle",
            "status": "IN_USE",
            "location": "Dodoma Regional Hospital",
            "purchase_date": "2023-06-15",
            "purchase_cost": 180000000.00,
            "ministry": "moh"
        }
    ]
}
```

**Python example:**

```python
import requests

BASE_URL = "http://192.168.100.18:8000/api"

# Step 1: Login (do this once every 30 minutes)
login_response = requests.post(f"{BASE_URL}/auth/login/", json={
    "username": "youth_ministry_api",
    "password": "G3n3rated!Str0ng#P@ss2024"
})
access_token = login_response.json()["access"]
headers = {"Authorization": f"Bearer {access_token}"}

# Step 2: Get assets
response = requests.get(f"{BASE_URL}/assets/", headers=headers, params={
    "page": 1,
    "page_size": 20,
    "status": "IN_USE"   # optional filter
})
data = response.json()

# Print each asset
for asset in data["results"]:
    print(f"{asset['asset_code']}: {asset['asset_name']} ({asset['status']})")

# Check if more pages exist
if data["next"]:
    next_page = data["next"]
    print(f"More results at: {next_page}")
```


<a name="7-7"></a>
### 7.7 Step 4: Token Expiry and Refresh

The access token expires after 30 minutes. When it expires, the API returns 401:

```json
// Response when token is expired:
// Status: 401 Unauthorized
{
    "detail": "Token is expired or invalid"
}
```

**How to handle this properly:**

```python
import requests
from datetime import datetime, timedelta

BASE_URL = "http://192.168.100.18:8000/api"

class GovAssetClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.access_token = None
        self.token_expiry = None
    
    def login(self):
        """Authenticate and get a fresh token."""
        response = requests.post(f"{BASE_URL}/auth/login/", json={
            "username": self.username,
            "password": self.password
        })
        data = response.json()
        self.access_token = data["access"]
        self.refresh_token = data["refresh"]
        # Assume token expires in 25 minutes (use 25 to be safe)
        self.token_expiry = datetime.now() + timedelta(minutes=25)
    
    def _ensure_token(self):
        """Refresh token if expired."""
        if not self.access_token or datetime.now() >= self.token_expiry:
            self.login()
    
    def get_assets(self, **params):
        """Fetch assets with automatic token refresh."""
        self._ensure_token()
        headers = {"Authorization": f"Bearer {self.access_token}"}
        response = requests.get(
            f"{BASE_URL}/assets/",
            headers=headers,
            params=params
        )
        if response.status_code == 401:
            # Token might have expired earlier than expected
            self.login()
            headers = {"Authorization": f"Bearer {self.access_token}"}
            response = requests.get(
                f"{BASE_URL}/assets/",
                headers=headers,
                params=params
            )
        response.raise_for_status()
        return response.json()

# Usage:
client = GovAssetClient("youth_ministry_api", "G3n3rated!Str0ng#P@ss2024")
assets = client.get_assets(status="IN_USE")
```


<a name="7-8"></a>
### 7.8 Available Endpoints for External Systems

| Method | Endpoint | Description | Permission Required |
|--------|----------|-------------|-------------------|
| POST | `/api/auth/login/` | Get JWT token | None (public) |
| POST | `/api/auth/verify-token/` | Verify our JWT token is valid | None (public) |
| GET | `/api/assets/` | List all assets | AUDITOR+ |
| GET | `/api/assets/{id}/` | Get one asset | AUDITOR+ |
| GET | `/api/assets/?status=DAMAGED` | Filter by status | AUDITOR+ |
| GET | `/api/assets/?category=Vehicle` | Filter by category | AUDITOR+ |
| GET | `/api/assets/?ministry=moh` | Filter by ministry | AUDITOR+ |
| POST | `/api/assets/` | Create an asset | MANAGER+ |
| PUT | `/api/assets/{id}/` | Update an asset | MANAGER+ |
| DELETE | `/api/assets/{id}/` | Delete an asset | ADMIN |
| GET | `/api/audit-logs/` | View audit history | ADMIN |
| GET | `/api/tenants/` | List all ministries/tenants | SUPER_ADMIN |

**Full URL patterns:**
- Dev: `http://192.168.100.18:8000/api/assets/`
- Prod: `https://api.govasset.go.tz/api/assets/`


<a name="7-9"></a>
### 7.9 How to Verify Our JWT Tokens (Optional)

If the other system wants to verify that OUR tokens are genuine (e.g., for a webhook), they can use:

```
POST http://192.168.100.18:8000/api/auth/verify-token/
Content-Type: application/json

{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
    "valid": true,
    "user_id": 1,
    "username": "youth_ministry_api",
    "role": "AUDITOR",
    "ministry_schema": null
}
```

This is useful if:
- We implement webhooks that send data TO their system
- They need to verify that requests actually came from us
- They don't want to store our shared secret


<a name="7-10"></a>
### 7.10 Error Handling Guide

**Common errors and how to fix them:**

```json
// 400 Bad Request — Missing required field
{
    "asset_name": ["This field is required."]
}
// Fix: Check the request body matches the serializer requirements
```

```json
// 401 Unauthorized — No token or expired token
{
    "detail": "Authentication credentials were not provided."
}
// Fix: Include Authorization: Bearer <token> header
```

```json
// 401 Unauthorized — Wrong credentials
{
    "detail": "No active account found with the given credentials"
}
// Fix: Check username and password
```

```json
// 403 Forbidden — Wrong role
{
    "detail": "You do not have permission to perform this action."
}
// Fix: The AUDITOR role is read-only. Use MANAGER or ADMIN role to create/edit
```

```json
// 404 Not Found — Wrong URL
{
    "detail": "Not found."
}
// Fix: Check the URL. Maybe the ID doesn't exist.
```

```json
// 429 Too Many Requests — Rate limited
{
    "detail": "Request was throttled. Expected available in 30 seconds."
}
// Fix: Slow down. Wait before making another request.
```


<a name="7-11"></a>
### 7.11 End-to-End Integration Test Plan

The external system should run this test sequence to verify integration works:

```python
# Integration test script
import requests

BASE = "http://192.168.100.18:8000/api"

def test_full_integration():
    print("1. Testing login endpoint...")
    r = requests.post(f"{BASE}/auth/login/", json={
        "username": "youth_ministry_api",
        "password": "G3n3rated!Str0ng#P@ss2024"
    })
    assert r.status_code == 200, f"Login failed: {r.status_code}"
    token = r.json()["access"]
    headers = {"Authorization": f"Bearer {token}"}
    print("   ✓ Login successful")

    print("2. Testing asset list...")
    r = requests.get(f"{BASE}/assets/", headers=headers, params={"page_size": 5})
    assert r.status_code == 200
    data = r.json()
    print(f"   ✓ Got {data['count']} total assets")
    assert "results" in data

    if data["count"] > 0:
        asset_id = data["results"][0]["id"]
        
        print("3. Testing single asset detail...")
        r = requests.get(f"{BASE}/assets/{asset_id}/", headers=headers)
        assert r.status_code == 200
        assert "asset_code" in r.json()
        print(f"   ✓ Got asset: {r.json()['asset_code']}")

    print("4. Testing filter by status...")
    r = requests.get(f"{BASE}/assets/", headers=headers, params={"status": "IN_USE"})
    assert r.status_code == 200
    print(f"   ✓ Filter by status works: {r.json()['count']} in-use assets")

    print("5. Testing filter by category...")
    r = requests.get(f"{BASE}/assets/", headers=headers, params={"category": "Vehicle"})
    assert r.status_code == 200
    print(f"   ✓ Filter by category works: {r.json()['count']} vehicles")

    print("6. Testing token verification...")
    r = requests.post(f"{BASE}/auth/verify-token/", json={"token": token})
    assert r.status_code == 200
    assert r.json()["valid"] == True
    print(f"   ✓ Token verified for user: {r.json()['username']}")

    print("7. Testing unauthorized write (AUDITOR cannot create)...")
    r = requests.post(f"{BASE}/assets/", headers=headers, json={
        "asset_name": "Test Asset"
    })
    assert r.status_code == 403
    print("   ✓ Write correctly rejected for AUDITOR role")

    print("\n✓ ALL TESTS PASSED")
    print("Integration is working correctly.")

if __name__ == "__main__":
    test_full_integration()
```


<a name="7-12"></a>
### 7.12 Security Best Practices for External Integrations

**For the external system:**
1. **Never hardcode passwords** in source code. Use environment variables or a secrets manager.
2. **Store JWT tokens in memory only**, never in files or databases.
3. **Always use HTTPS in production** — never send credentials over plain HTTP.
4. **Check for 401 responses** and handle token refresh automatically.
5. **Log all API activity** for audit purposes.

**For us (the API provider):**
1. **Use service accounts** — not real user accounts — for machine-to-machine access.
2. **Set appropriate roles** — AUDITOR for read-only, never SUPER_ADMIN.
3. **Rotate passwords** on a regular schedule (e.g., every 90 days).
4. **Monitor API usage** — watch for unusual patterns or sudden spikes.
5. **Revoke access immediately** if a system no longer needs integration.
6. **Rate-limit per service account** to prevent abuse.


<a name="7-13"></a>
### 7.13 Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│              API INTEGRATION QUICK REFERENCE CARD                │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. GET CREDENTIALS                                              │
│     Ask Super Admin to create a service account for your system  │
│     You'll receive: username, password, role, API URL            │
│                                                                   │
│  2. LOGIN                                                        │
│     POST  /api/auth/login/                                       │
│     Body: {"username": "x", "password": "y"}                     │
│     Response: {"access": "token...", "refresh": "token..."}      │
│                                                                   │
│  3. CALL API                                                     │
│     GET  /api/assets/                                             │
│     Header: Authorization: Bearer <token>                         │
│     Response: {"count": N, "results": [...]}                      │
│                                                                   │
│  4. REFRESH                                                      │
│     Token expires in 30 minutes. Get a new one via login.        │
│                                                                   │
│  COMMON ENDPOINTS:                                               │
│     GET    /api/assets/              List assets (paginated)     │
│     GET    /api/assets/{id}/         Get one asset               │
│     GET    /api/auth/verify-token/   Verify a token              │
│                                                                   │
│  FILTERS:                                                         │
│     ?status=IN_USE&category=Vehicle&ministry=moh                 │
│     ?page=2&page_size=50                                          │
│     ?search=ambulance                                              │
│                                                                   │
│  EXAMPLE (Python):                                                │
│     import requests                                               │
│     r = requests.post(url + '/auth/login/', json=creds)          │
│     h = {'Authorization': 'Bearer ' + r.json()['access']}        │
│     assets = requests.get(url + '/assets/', headers=h).json()    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```


<a name="7-14"></a>
### 7.14 Panel Questions for Chapter 7

**Q: What happens if the external system sends too many requests?**
A: Our API has rate limiting (throttling). In dev, it's 100 requests per hour per user. In production with Nginx, it can be set higher. The system receives a 429 status code and must wait before retrying.

**Q: Can an external system GET a specific asset by asset_code instead of database ID?**
A: Currently, filtering by asset_code is supported: `GET /api/assets/?search=MOH-AMB-001`. The `search` parameter matches against asset_code, asset_name, and other text fields. If you need a dedicated lookup endpoint, we can add it.

**Q: Do external systems need to handle pagination?**
A: Yes. Our API returns paginated results (20 per page by default). The response includes `count`, `next`, `previous`, and `results`. Your code should follow the `next` URL to get all results, or set `page_size` to a higher value (max 100).

**Q: Does the external system see all historical data or just current?**
A: That depends on the API endpoint. Asset endpoints show current data. Audit log endpoints show historical changes. A service account with AUDITOR role can only see current data, not audit logs. ADMIN role is needed for audit logs.

**Q: Can we set up webhooks so our system is notified when assets change?**
A: Not yet. Currently, the external system must poll (check periodically). We can add webhooks in a future version. For now, polling every 5-15 minutes is the recommended approach.


<a name="7-15"></a>
### 7.15 Beginner Misconceptions

**Misconception:** "The external system needs to install something on their server."
**Truth:** No installation needed. They just make HTTP requests to our API. Any programming language that can make HTTP requests can integrate.

**Misconception:** "The external system needs direct database access."
**Truth:** They never touch our database. All access goes through the API, which enforces authentication and permissions.

**Misconception:** "If their token expires mid-request, the data is lost."
**Truth:** Their code should check for 401 responses and retry with a fresh token. A well-written client handles this transparently.

**Misconception:** "External systems can see everything."
**Truth:** They can only see what their role and ministry_schema allow. An AUDITOR with ministry_schema='moh_schema' can only see MOH data, read-only.

**Misconception:** "We need a separate API for each external system."
**Truth:** One API serves all external systems. Each system authenticates with its own service account, and permissions are enforced per account.
