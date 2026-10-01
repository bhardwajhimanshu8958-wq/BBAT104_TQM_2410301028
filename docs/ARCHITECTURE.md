# System Architecture

**Project:** BBAT104 TQM — Parking Management System  
**Version:** 1.0 | Date: 2026-10-01

---

## 1. Layered Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     UI Layer (Streamlit)                      │
│  ui_pages/pg_dashboard.py  pg_slots.py  pg_vehicles.py       │
│  pg_entry.py  pg_exit.py  pg_reports.py  pg_calendar.py      │
│  pg_search.py  pg_checksheet.py  pg_fmea.py  pg_pareto.py   │
│  pg_fishbone.py  pg_pdca.py  pg_settings.py                  │
├──────────────────────────────────────────────────────────────┤
│              Feature + TQM Layer                              │
│  features/theme.py       features/dashboard.py               │
│  features/search_filters.py  features/calendar_view.py       │
│  tqm/checksheet.py  tqm/fmea.py  tqm/pareto.py              │
│  tqm/fishbone.py  tqm/pdca.py                                │
├──────────────────────────────────────────────────────────────┤
│              Business Logic Layer                             │
│  modules/slots.py    modules/vehicles.py                     │
│  modules/sessions.py  modules/billing.py                     │
│  modules/validation.py  modules/reports.py                   │
├──────────────────────────────────────────────────────────────┤
│              Data Layer                                       │
│  database/db.py  ── context manager, init_db()               │
│  database/schema.sql  database/seed.py                       │
│  SQLite: parking.db                                          │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Vehicle Entry-to-Exit Process Flowchart

```mermaid
flowchart TD
    A([Operator opens Entry page]) --> B[Select Vehicle by plate]
    B --> C{Vehicle found\nin DB?}
    C -- No --> D[Register new vehicle first]
    D --> B
    C -- Yes --> E{Vehicle already\nhas active session?}
    E -- Yes --> F[/Show error: vehicle already parked/]
    F --> B
    E -- No --> G[Auto-suggest first Available slot\nmatching vehicle type]
    G --> H{Slot available?}
    H -- No --> I[/Show warning: no slots free/]
    H -- Yes --> J[Operator confirms entry]
    J --> K[Create parking_session row\nentry_time = NOW, status = Active]
    K --> L[Set slot status = Occupied]
    L --> M([Entry recorded ✓])

    M --> N([... vehicle parks ...])

    N --> O([Operator opens Exit page])
    O --> P[Select active session by vehicle]
    P --> Q[Calculate duration\nduration = exit_time − entry_time]
    Q --> R{duration ≤ free_minutes?}
    R -- Yes --> S[fee = base_rate]
    R -- No --> T["fee = base_rate + ⌈(duration − free_minutes) / 60⌉ × per_hour_rate"]
    S --> U[Update session: exit_time, fee, status = Completed]
    T --> U
    U --> V[Set slot status = Available]
    V --> W([Exit recorded ✓ — Slot freed])
```

---

## 3. Application Module Dependency Diagram

```mermaid
graph LR
    app[app.py] --> ui[ui_pages/*]
    ui --> feat[features/*]
    ui --> mod[modules/*]
    ui --> tqm[tqm/*]
    feat --> mod
    feat --> db[database/db.py]
    mod --> db
    tqm --> db
    mod --> cfg[config.py]
    feat --> cfg
    db --> sql[(SQLite\nparking.db)]
```

---

## 4. Database Entity-Relationship Overview

```mermaid
erDiagram
    slots {
        INTEGER slot_id PK
        TEXT slot_code
        TEXT zone
        TEXT slot_type
        TEXT status
    }
    vehicles {
        INTEGER vehicle_id PK
        TEXT plate_no
        TEXT owner_name
        TEXT phone
        TEXT vehicle_type
        TEXT created_at
    }
    parking_sessions {
        INTEGER session_id PK
        INTEGER vehicle_id FK
        INTEGER slot_id FK
        TEXT entry_time
        TEXT exit_time
        REAL fee
        TEXT status
    }
    tariff {
        TEXT vehicle_type PK
        REAL base_rate
        REAL per_hour_rate
        INTEGER free_minutes
    }
    settings {
        TEXT key PK
        TEXT value
    }
    defects {
        INTEGER defect_id PK
        TEXT date_found
        TEXT module
        TEXT description
        TEXT fishbone_category
        TEXT defect_type
        INTEGER severity
        TEXT status
        TEXT resolution
        INTEGER is_demo
    }
    fmea {
        INTEGER fmea_id PK
        TEXT process_step
        TEXT failure_mode
        TEXT effect
        TEXT cause
        INTEGER severity
        INTEGER occurrence
        INTEGER detection
        INTEGER rpn
        TEXT mitigation
        TEXT status
    }
    pdca {
        INTEGER pdca_id PK
        INTEGER cycle_no
        TEXT plan
        TEXT do_action
        TEXT check_result
        TEXT act_decision
        TEXT metric_name
        REAL before_value
        REAL after_value
        TEXT date
    }

    vehicles ||--o{ parking_sessions : "has"
    slots ||--o{ parking_sessions : "holds"
    tariff ||--o{ parking_sessions : "prices"
```

---

## 5. Technology Choices — Rationale

| Technology | Why chosen |
|------------|-----------|
| **Streamlit** | Rapid Python-native web UI; no JS/HTML required; page-based navigation with `st.navigation` suits a multi-module project |
| **SQLite3** | Zero-configuration embedded database; adequate for single-operator desktop use; schema enforced with CHECK constraints |
| **pandas** | Industry-standard DataFrame library; simplifies group-by, pivoting, and Excel export |
| **openpyxl** | Backend for pandas `.to_excel()`; allows header formatting and column-width control |
| **matplotlib + seaborn** | Standard SQC chart libraries; Pareto and Fishbone are well-supported; integrate with Streamlit via `st.pyplot()` |
| **pytest** | De-facto Python testing standard; supports both unit tests and Streamlit's `AppTest` smoke tests |
