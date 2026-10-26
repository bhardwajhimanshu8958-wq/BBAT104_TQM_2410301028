# Autonomous Smart Parking Management System (AS-PMS)

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI_0.115-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python)](https://python.org)
[![SQLite](https://img.shields.io/badge/Database-SQLite_WAL-003B57.svg?logo=sqlite)](https://sqlite.org)
[![TailwindCSS](https://img.shields.io/badge/UI-TailwindCSS_CDN-38B2AC.svg?logo=tailwind-css)](https://tailwindcss.com)
[![Architecture](https://img.shields.io/badge/Architecture-Decoupled_Client--Server-6366F1.svg)](docs/SYSTEM_ARCHITECTURE.md)

An enterprise-grade, multi-tiered parking management and automation platform designed for academic viva evaluation and real-world industrial operations. Features strict 3-tier Role-Based Access Control (RBAC), Grokking OOD vehicle-to-stall compatibility rules, atomic pessimistic row-locking to eliminate double-booking, an automated background lifespan reaper daemon, and dynamic multi-floor expansion.

---

## Clean Directory Tree

```
parking-management/
├── backend/
│   ├── main.py              # FastAPI application gateway, routes, lifespan worker & static mount
│   ├── models.py            # SQLAlchemy 2.0 ORM schemas, Enums & Grokking OOD compatibility engine
│   ├── database.py          # SQLite engine config, thread-safe RLock & WAL mode PRAGMAs
│   ├── auth.py              # Cryptographic BCrypt hashing, JWT generation & RBAC guards
│   ├── schemas.py           # Pydantic v2 validation models & request/response contracts
│   ├── requirements.txt     # Locked production dependencies
│   └── parking_management.db# Relational SQLite database with WAL journals
├── frontend/
│   └── index.html           # Unified industrial single-page dashboard with role portals
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md # Full architecture specification, Mermaid diagrams & math models
│   └── SRS.md                 # IEEE-compliant Software Requirements Specification (FR-1 to FR-5)
└── README.md                # Project documentation, quickstart & 3-minute viva runbook
```

---

## Quickstart Guide

### 1. Prerequisites
- Python 3.10 or higher
- PowerShell or modern terminal

### 2. Setup & Execution
From the root directory, navigate into `backend/`, install requirements, and launch the Uvicorn ASGI server:

```powershell
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Once launched, access the application in your browser:
- **Interactive Web Portal**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## Default Credentials

The platform initializes with pre-seeded accounts configured for seamless testing across all three operational tiers:

| Role Tier | Username | Password | Operational Capabilities |
|:---|:---|:---|:---|
| **Chief Administrator** | `admin1` | `admin123` | System tariffs, live revenue stats, floor/stall master, dynamic expansion, and immutable audit logs. |
| **Gate Attendant / Operator** | `gateman1` | `gate123` | 1-Click pending booking intake, optical ticket dispenser, barrier servo telemetry, and POS checkout terminal. |
| **Registered Customer** | `driver1` | `driver123` | Live multi-floor stall availability, advance reservation engine, optical digital gate passes, and online UPI settlement. |

---

## Key Engineering Features

1. **Grokking OOD Vehicle Compatibility**:
   - `MOTORBIKE` $\to$ `MOTORBIKE`, `COMPACT`, `LARGE`
   - `CAR` $\to$ `COMPACT`, `LARGE`
   - `VAN` / `TRUCK` $\to$ `LARGE` strictly
   - `ELECTRIC` $\to$ `ELECTRIC`, `COMPACT`, `LARGE`
   - Strict size checking rejects mismatches (e.g., CAR into MOTORBIKE stall) with `HTTP 400 Bad Request`.

2. **Concurrency & Double-Booking Elimination**:
   - Uses SQLite in Write-Ahead Logging (`WAL`) mode with `busy_timeout=5000`.
   - Combines Python re-entrant locks (`threading.RLock`) with SQLAlchemy `with_for_update()` pessimistic row locks.
   - Guaranteed: when two requests race for the same stall in the same millisecond, the 1st request wins (`200 OK`) and the 2nd request receives `HTTP 409 Conflict`.

3. **Background Lifespan Reaper Daemon**:
   - Runs continuously via FastAPI's `lifespan` context manager.
   - Sweeps every 60 seconds. Reclaims unfulfilled reservations after 15 minutes of inactivity back to `AVAILABLE`.
   - Expired passes are barred at the gate with `HTTP 400 Bad Request` and barrier locked.

4. **1-Click Operator Inbound Flow**:
   - The gate terminal displays a real-time "Pending Bookings" quick-select list of all active `RESERVED` tickets.
   - Clicking any pending badge auto-populates the vehicle license plate, ticket ID, and category instantly.

5. **Accurate Tiered Tariff & Overstay Engine**:
   - Immediate Exit Grace Period: $\le 2$ minutes AND no overstay $\to$ ₹0.00.
   - Progressive tiers: 1st hour ₹50, 2nd-3rd hour ₹30/hr, 4th+ hour ₹20/hr.
   - Overstay Multiplier: Excess hours past booked end window incur a statutory $1.5\times$ penalty multiplier.
   - Non-Conflicting Settlement: Pre-paid tickets display `✓ DIGITAL PASS SETTLED (₹[amount]) — EXIT CLEARED` and scan at exit with `Net Due: ₹0.00`. Subsequent duplicate payments return `HTTP 400`.

---

## Step-by-Step 3-Minute Viva Presentation Runbook

Follow this precise sequence during viva examination or academic project demonstration:

```
[00:00 - 00:45] Login & Architectural Overview
  1. Open http://127.0.0.1:8000/ -> Display industrial login screen.
  2. Log in as 'admin1' / 'admin123'.
  3. Show Chief Administrator dashboard: Live Floor Gauges, Dynamic Floor Expansion (P1, P2, P3), System Tariffs, and immutable Financial Audit Trail.
  4. Explain Decoupled Client-Server architecture and SQLite WAL mode (refer to docs/SYSTEM_ARCHITECTURE.md).

[00:45 - 01:30] Customer Pre-Booking & Grokking OOD Rules
  1. Log out, then log in as 'driver1' / 'driver123'.
  2. Show live multi-floor occupancy map.
  3. Select Floor 1 -> Click an available COMPACT stall (e.g. P1-C01) -> Reserve for vehicle 'KA-01-VIVA-01' (CAR).
  4. Show generated Active Digital Gate Pass with optical code.

[01:30 - 02:15] 1-Click Gate Operator Intake & Vehicle Compatibility
  1. Log out, then log in as 'gateman1' / 'gate123'.
  2. In the Gate Inbound Terminal, show the 'Pending Bookings' quick-select drawer.
  3. Click the badge for 'KA-01-VIVA-01' -> Inputs and vehicle type auto-populate with 1 click!
  4. Click 'Issue Ticket & Raise Inbound Barrier' -> Barrier servo opens (Green), stall transitions to PARKED (Red).
  5. Demonstrate OOD Rejection: Attempt to check in a CAR into a MOTORBIKE stall -> Observe instant red toast and HTTP 400 "Size Mismatch: Vehicle cannot fit in this stall."

[02:15 - 03:00] Mobile UPI Pre-Payment & Exit Gate Settlement
  1. Switch back to Customer portal or demonstrate live in POS Outbound Exit.
  2. In Customer portal, click 'Pay Online via UPI / Card' -> Observe green receipt banner:
     "✓ DIGITAL PASS SETTLED (₹[amount]) — EXIT CLEARED".
  3. Switch to Operator Outbound Exit -> Scan ticket -> System displays:
     "PAYMENT VERIFIED: Settled Online via UPI. Net Due: ₹0.00" -> Exit barrier raises!
  4. Open 'Supervisor Diagnostics & Edge-Case Console' at screen bottom:
     - Run 'Multi-Vehicle Concurrency Stress Test' -> First vehicle gets 200 OK, second gets 409 Conflict!
     - Run 'Simulate Overstay' -> Demonstrates itemized 1.5x penalty multiplier.
```

---

## Technology Stack Summary

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com)
- **ASGI Server**: [Uvicorn](https://www.uvicorn.org)
- **ORM & Data Layer**: [SQLAlchemy 2.0](https://www.sqlalchemy.org)
- **Concurrency & WAL**: SQLite 3 with Write-Ahead Logging & thread-safe re-entrant mutexes
- **Authentication**: Stateless JSON Web Tokens (`PyJWT`) with salted BCrypt password encryption
- **Frontend Layer**: Semantic HTML5, Vanilla JavaScript (ES6+), Tailwind CSS CDN, FontAwesome 6 Icons
- **Documentation**: IEEE 830-compliant SRS (`docs/SRS.md`) and Technical Architecture (`docs/SYSTEM_ARCHITECTURE.md`)
