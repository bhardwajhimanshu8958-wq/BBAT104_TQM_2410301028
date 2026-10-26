# Industrial Enterprise Parking Management System

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://python.org)
[![SQLite](https://img.shields.io/badge/Database-SQLite_WAL-003B57.svg?logo=sqlite)](https://sqlite.org)
[![Architecture](https://img.shields.io/badge/Architecture-Decoupled_Client--Server-6366F1.svg)](docs/SYSTEM_ARCHITECTURE.md)
[![Specifications](https://img.shields.io/badge/Standards-IEEE_830_SRS-emerald.svg)](docs/SRS.md)

---

## 1. Project Overview

The **Industrial Enterprise Parking Management System** is a mission-critical, high-concurrency client-server parking platform engineered for resilient facility operations. It integrates automated spatial stall assignment, dynamic tiered tariff computation, strict role-based access control (RBAC), and real-time hardware telemetry into a decoupled, low-latency architecture.

Designed to eliminate double-booking hazards and handle burst concurrency, the system orchestrates automated multi-tier stall reservations, inbound optical gate validation, outbound point-of-sale (POS) terminal settlements, and autonomous background reclamation of abandoned reservation holds.

---

## 2. System Architecture

The platform adheres to a decoupled client-server topology designed for modularity, sub-millisecond local latency, and zero cross-tier privilege escalation.

### Client-Server Architecture

* **Frontend Client Tier**: A responsive Single-Page Application (`frontend/index.html`) developed with standard HTML5, Vanilla ES6+ JavaScript, and Tailwind CSS. Employs CSS custom properties (variables) for real-time dynamic industrial palette shifting and persistent state management via `localStorage`.
* **Backend Application Gateway**: An asynchronous REST API (`backend/main.py`) powered by **FastAPI** running atop an ASGI **Uvicorn** server. Leverages **Pydantic v2** for request/response serialization and schema enforcement, coupled with **SQLAlchemy 2.0 ORM** for persistent data transactions.
* **Database Storage Tier**: Embedded **SQLite 3** operating in **Write-Ahead Logging (WAL)** mode (`PRAGMA journal_mode=WAL;`, `PRAGMA synchronous=NORMAL;`) with a 5000ms busy timeout (`busy_timeout=5000`). This ensures non-blocking concurrent reads while maintaining ACID transactional guarantees during high-frequency writes.
* **Autonomous Background Worker**: A non-blocking asynchronous `asyncio` background daemon running within the FastAPI application lifespan context manager. Performs periodic sweeps to enforce unfulfilled hold expirations and resource recycling without blocking inbound request loops.

### System Architecture Diagram

```
+----------------------------------------------------------------------------------------------------+
|                                           FRONTEND CLIENTS                                         |
|  Single-Page Application (HTML5 / Vanilla JS ES6+ / Tailwind CSS / Dynamic CSS Theme Engine)       |
|  +------------------------+  +--------------------------+  +------------------------------------+  |
|  | Customer / Driver View |  | Gate Operator POS View   |  | Chief Administrator View           |  |
|  +------------------------+  +--------------------------+  +------------------------------------+  |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   | HTTP / REST (Bearer JSON Web Tokens)
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                         FASTAPI API GATEWAY                                        |
|  ASGI Server (Uvicorn) • Request Routing • Pydantic v2 Contract Validation                         |
|  +-----------------------------------------------+  +-------------------------------------------+  |
|  | Authentication & Security (PyJWT, BCrypt)     |  | Role-Based Access Control (RBAC Guards)   |  |
|  +-----------------------------------------------+  +-------------------------------------------+  |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+----------------------------------------------------------------------------------------------------+
|                                     BUSINESS LOGIC & ENGINE LAYER                                  |
|  +---------------------------+  +-------------------------------+  +----------------------------+  |
|  | Vehicle-to-Stall Rules    |  | Dynamic Tariff & Surcharge    |  | Concurrency Control        |  |
|  | (Spatial Compatibility)   |  | (Tiered Rates, Overstay 1.5x) |  | (Row Locks, Mutex Locks)   |  |
|  +---------------------------+  +-------------------------------+  +----------------------------+  |
+------------------------------------+-----------------------------------------------+---------------+
                                     |                                               ^
                                     v                                               |
+------------------------------------------------------------+   +-------------------+---------------+
|              DATABASE STORAGE LAYER (SQLAlchemy ORM)       |   |          BACKGROUND WORKER        |
|  SQLite 3 (WAL Mode, PRAGMA synchronous=NORMAL)            |   |  Asyncio Lifespan Reaper Daemon   |
|  busy_timeout=5000 • Atomic Transactions • ACID Compliance |<--|  15-min Unfulfilled Hold Sweeper  |
+------------------------------------------------------------+   +-----------------------------------+
```

---

## 3. Directory Layout

```
parking-management/
├── backend/
│   ├── main.py              # Application entrypoint, FastAPI gateway, routes & lifespan daemon
│   ├── models.py            # SQLAlchemy ORM models, domain entities & spatial rule definitions
│   ├── database.py          # Database session management, engine configuration & WAL pragmas
│   ├── auth.py              # Cryptographic password hashing, JWT signing & RBAC dependencies
│   ├── schemas.py           # Pydantic v2 schemas and request/response contracts
│   └── requirements.txt     # Locked production dependencies
├── frontend/
│   └── index.html           # Unified industrial single-page application & responsive theme engine
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md # Detailed architectural breakdown, schemas & flow specifications
│   └── SRS.md               # Software Requirements Specification (IEEE 830 compliant)
└── README.md                # Principal technical documentation & deployment guide
```

---

## 4. Core Business Logic & Rules

### Vehicle-to-Stall Spatial Allocation

The system enforces object-oriented physical compatibility rules between vehicle dimensions and stall classifications:

| Vehicle Classification | Permissible Parking Stall Types | Constraint Logic |
|:---|:---|:---|
| **MOTORBIKE** | `MOTORBIKE`, `COMPACT`, `LARGE` | Minimal physical footprint; allowed in all standard stall types. |
| **CAR** | `COMPACT`, `LARGE` | Incompatible with `MOTORBIKE` stalls due to spatial boundaries. |
| **VAN** / **TRUCK** | `LARGE` | Strictly restricted to heavy-duty, long-wheelbase stalls only. |
| **ELECTRIC (EV)** | `ELECTRIC`, `COMPACT`, `LARGE` | Prioritized for EV stalls with charging infrastructure; fallback to standard stalls. |

* **Enforcement**: Any inbound check-in or pre-booking reservation attempting to place an incompatible vehicle into an invalid stall (e.g., placing a `CAR` into a `MOTORBIKE` slot) is rejected immediately with **`HTTP 400 Bad Request`**.

### Dynamic Tariff & Surcharge Engine

Tariff computations run dynamically on live duration timestamps and maintain complete audit traceability:

* **Grace Period**: Immediate exits within **$\le 2$ minutes** incur an administrative fee of **₹0.00**.
* **Tiered Base Rates**:
  * First Hour ($0 < t \le 1$ hr): Base fixed rate (default: ₹40.00/hr).
  * Second & Third Hours ($1 < t \le 3$ hrs): Tier 2 rate (default: ₹35.00/hr).
  * Subsequent Hours ($t > 3$ hrs): Tier 3 rate (default: ₹25.00/hr).
* **1.5x Overstay Surcharge**: Automatically calculated whenever actual parked duration surpasses the scheduled reservation window:
  $$\text{Overstay Surcharge} = \text{Overstay Hours} \times \text{Base Rate} \times 1.5$$
* **Flat Lost-Ticket Assessment**: Unrecognized plates or lost ticket overrides trigger a statutory administrative fee of **₹500.00**.

### Concurrency Management

To prevent race conditions and double-booking during burst traffic loads:
* Combines thread-safe re-entrant mutexes (`threading.RLock`) with SQLAlchemy row-level pessimistic locks (`SELECT ... with_for_update()`).
* When concurrent transactions compete for the identical slot within the same millisecond window, the primary transaction acquires the lock and commits successfully (**`HTTP 200 OK`**), while competing requests are safely aborted with **`HTTP 409 Conflict`** ("Stall already reserved/occupied by another vehicle").

### Automated No-Show Hold Release

* An autonomous background lifespan daemon sweeps active bookings every 60 seconds.
* Reservations lingering in `RESERVED` status beyond **15 minutes** past their scheduled booking timestamp without gate check-in are marked `EXPIRED`.
* The allocated parking stall is immediately restored to `AVAILABLE`, maximizing facility inventory utilization.
* Expired passes presented at the gate panel are barred with an **`HTTP 400 Bad Request`** rejection.

---

## 5. UI/UX & Usability Systems

### Dark / Light Mode Engine
* Implements a persistent, zero-dependency theme engine.
* Toggles between an ultra-low-strain dark industrial palette (`#070a12` background with `#0f172a` panels) and a daylight paper style (`#f8fafc` background with `#ffffff` panels).
* User preference is cached across sessions via `localStorage.getItem('ui_mode')`.

### Custom Industrial Palettes
Features dynamic CSS variable runtime injection driven by `html[data-theme="..."]`:
* **Siemens Slate (Default)**: Cyan accent (`--theme-primary: #38bdf8`, `--theme-primary-border: #0284c7`).
* **Bosch Amber**: Warning industrial yellow (`--theme-primary: #f59e0b`, `--theme-primary-border: #d97706`).
* **Emerald Eco**: High-contrast mint green (`--theme-primary: #10b981`, `--theme-primary-border: #059669`).
* Global utility bindings (`theme-btn`, `theme-text`, `theme-border`, `theme-bg-subtle`, `theme-glow`) dynamically update buttons, active navigation bars, KPI tags, and stall borders instantly without page reloads.

### Glanceable KPI Dashboard
* Sticky telemetry strip providing high-density facility metrics at a glance.
* Real-time capacity occupancy bar with color transition thresholds.
* Real-time breakdown pills displaying exact counts for `Available`, `Reserved`, `Parked`, and `Maintenance` stalls.
* Instant financial shift counter tracking daily cumulative revenue and active ticket counts.
* Hardware telemetry indicator displaying inbound/outbound barrier state (`LOWERED` vs `RAISED`).

### Real-Time Search & Multi-Filters
* Instant client-side filtering across stall maps and customer ticket passes.
* Dual-input matching on license plates, ticket identifiers, vehicle categories, and slot IDs.
* Responsive multi-floor visual matrix highlighting slot states with distinct industrial badges.

### Calendar & Date-Range Query Tool
* Interactive temporal range selector (`start_date` to `end_date`) supporting single-day audits and multi-day interval sweeps.
* Built-in rapid presets: `Today`, `Yesterday`, and `Last 7 Days`.
* Interrogates `/api/admin/audit-ledger` and recalculates aggregated revenue, transaction volume, and administrative overrides over the chosen historical window.

---

## 6. Role-Isolated Operations & Diagnostics

Access privileges are enforced through cryptographic JWT bearer validation:

### 1. Customer / Driver Portal
* **Live Vacancy Discovery**: Live inspection of available stalls across all facility tiers.
* **Self-Service Pre-Booking**: Automated reservation with license plate registration and duration commitment.
* **Digital Entry Pass**: Optical QR/barcode display, slot routing data, and live hold validity countdown timer.
* **Fast-Action Sandbox**:
  * *1-Click Demo Booking*: Automatically discovers an available stall and generates a live demo ticket pass.
  * *Fast-Forward 15m Expiry*: Simulates hold expiration to verify background slot deallocation.

### 2. Gate Operator Portal
* **Inbound Lane Terminal**:
  * Real-time "Pending Bookings" quick-select drawer.
  * 1-Click auto-population of vehicle plate, category, and assigned stall.
  * Optical ticket issuance and servo barrier actuation (`RAISE`).
* **Outbound POS Terminal**:
  * Optical ticket scanner with live itemized breakdown (Base Rate, Overstay Penalty, Total Due).
  * Multi-method payment settlement supporting `CASH`, `UPI_ONLINE`, and `FASTAG_RFID`.
  * Thermal receipt generator with modal preview and formatted print stylesheet.
* **Integrated Hardware & Edge-Case Simulators**:
  * **SIM 1 (Concurrency Race)**: Concurrent stress-test testing atomic slot allocation under concurrent load.
  * **SIM 2 (Dynamic Overstay)**: Injects artificial overstay timestamps (+1h, +3h, +6h, +12h) to validate 1.5x surcharge calculations.
  * **SIM 5 (Safety Sensor Rebound)**: Simulates physical obstacle detection during barrier closure, triggering an immediate safety rebound cycle.
  * **SIM 7 (Lost Ticket Override)**: Assesses statutory lost ticket fee (₹500.00), appends audit trail entry, and clears the exit gate.

### 3. Chief Administrator Portal
* **Facility Topology Governance**: Real-time management of floors, stall inventories, and dynamic multi-tier floor provisioning.
* **FAILOVER-03 Sector Quarantine**: Emergency facility lockdown control to transition entire floors into `MAINTENANCE` mode.
* **3-Vector RBAC Security Matrix**: Automated penetration testing tool validating that cross-role access attempts (Operator accessing Admin rates, Customer accessing Gate check-in, Anonymous accessing Audit logs) return strict `403 Forbidden` and `401 Unauthorized` responses.
* **Master Audit Ledger**: Immutable system event stream tracking all vehicle entries, exits, barrier overrides, rate alterations, and background daemon actions.

---

## 7. Default Credentials

The platform initializes with pre-seeded accounts configured for immediate authentication across all operational roles:

| Operational Role | Username | Password | Access Scope |
|:---|:---|:---|:---|
| **Chief Administrator** | `admin1` | `admin123` | Full system governance, rate tariffs, dynamic floor provisioning, audit ledger, and sector quarantine. |
| **Gate Operator** | `gateman1` | `gate123` | Inbound barrier terminal, outbound POS cashier, thermal receipts, and lane edge-case simulators. |
| **Customer / Driver** | `driver1` | `driver123` | Public vacancy board, self-service slot reservation, digital passes, and mobile UPI settlement. |

---

## 8. Installation & Setup

### Prerequisites
* **Python**: Version 3.10 or higher.
* **Package Manager**: `pip` (included with standard Python distributions).
* **Operating System**: Platform-agnostic (Windows, Linux, macOS).

### Step-by-Step Installation

1. **Clone or Navigate to the Workspace**:
   ```bash
   cd parking-management
   ```

2. **Establish a Virtual Environment** (Recommended):
   ```bash
   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate

   # Windows PowerShell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. **Launch the Application**:
   Execute Uvicorn to run the FastAPI service. SQLite tables, default tariffs, floor structures, and operational user accounts are seeded automatically on startup:
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```

### Operational Endpoints

Once the application is initialized, access the following local endpoints:

* **Interactive Web Application**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* **Interactive OpenAPI Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Alternative API Documentation (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 9. Security & Compliance

* **Authentication Guard**: Stateless JSON Web Tokens (`HS256`) signed with cryptographic expiry validation.
* **Credential Encryption**: Industry-standard **BCrypt** with salted hashing routines.
* **Privilege Segregation**: Dependency injection guards (`require_role`) enforce strict role boundaries on every administrative and operational endpoint.
* **Database Concurrency Security**: WAL journaling prevents database locks and ensures transactional integrity under load.
