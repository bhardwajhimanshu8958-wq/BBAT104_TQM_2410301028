# Software Requirements Specification (SRS)

**Project:** Parking Management System  
**Course:** BBAT104 — Fundamentals of Total Quality Management  
**Student:** Himanshu Bhardwaj | Roll No. 2410301028  
**Version:** 1.0 | Date: 2026-10-01  

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements of the **Parking Management System** developed as part of BBAT104 TQM Session 2026-27. It serves as the contract between the developer and the course evaluator, and as the baseline for test design and TQM traceability.

### 1.2 Scope
The system is a desktop-grade web application built with Python and Streamlit. It manages parking slots, vehicle registrations, entry/exit sessions, billing, and generates TQM quality charts. It is deployed locally and requires no internet access beyond the initial `pip install`.

### 1.3 Definitions and Acronyms

| Term | Definition |
|------|------------|
| CRUD | Create, Read, Update, Delete |
| CTQ | Critical-to-Quality |
| FMEA | Failure Mode and Effects Analysis |
| PDCA | Plan-Do-Check-Act |
| Poka-Yoke | Mistake-proofing technique (Japanese) |
| RPN | Risk Priority Number = Severity × Occurrence × Detection |
| SQC | Statistical Quality Control |
| TQM | Total Quality Management |
| Utilization | Occupied slots ÷ Total non-maintenance slots × 100% |

---

## 2. Overall Description

### 2.1 Product Perspective
The system is a standalone application that replaces manual parking registers. It persists all data in an SQLite database and produces Excel reports and quality charts.

### 2.2 User Classes

| Class | Description |
|-------|-------------|
| Parking Operator | Primary user: manages slots, vehicles, entry/exit, billing, and views TQM charts |
| Administrator | Same as operator for this single-user system |
| Course Evaluator | Read-only reviewer assessing the GitHub repository and documentation |

### 2.3 Operating Environment
- OS: Windows / macOS / Linux  
- Python: 3.10+  
- Browser: Any modern browser (Streamlit renders the UI)  
- Storage: SQLite file (`parking.db`) on local disk  

### 2.4 Assumptions and Constraints
- **AC-1:** The system will be operated by a single user at a time.
- **AC-2:** All monetary values are in Indian Rupees (₹).
- **AC-3:** Vehicle plates follow Indian format (e.g., `UK07AB1234`).
- **AC-4:** The system does not integrate with physical hardware (barriers, sensors).
- **AC-5:** Time is measured in hours; fractional hours are rounded up for billing.

---

## 3. Functional Requirements

### 3.1 Slot Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | The system shall allow the operator to create a parking slot with attributes: slot code, zone, slot type (Car/Bike/EV/Disabled), and status. | High |
| FR-02 | Slot codes shall be unique; the system shall reject duplicates. | High |
| FR-03 | The system shall allow updating slot details and status. | High |
| FR-04 | The system shall allow deleting a slot only if its status is NOT 'Occupied'. | High |
| FR-05 | The system shall display all slots with filters by zone, type, and status. | Medium |

### 3.2 Vehicle Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-06 | The system shall allow registering a vehicle with plate number, owner name, phone, and vehicle type. | High |
| FR-07 | Plate numbers shall be unique; the system shall reject duplicate registrations. | High |
| FR-08 | The system shall allow updating and deleting vehicle records. | Medium |
| FR-09 | Plate numbers shall match the Indian vehicle plate regex pattern. | High |

### 3.3 Entry Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-10 | The system shall register a vehicle's entry by selecting vehicle and auto-suggesting the first available slot of the matching type. | High |
| FR-11 | On entry, the selected slot status shall change to 'Occupied' and an active session record shall be created with the current timestamp. | High |
| FR-12 | The system shall prevent entry of a vehicle that already has an active session. | High |

### 3.4 Exit Management

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-13 | The system shall register a vehicle's exit by selecting the active session. | High |
| FR-14 | On exit, the system shall compute the fee: if duration ≤ free minutes, fee = base rate; otherwise fee = base rate + ⌈(duration − free minutes) / 60⌉ × per-hour rate. | High |
| FR-15 | On exit, the session status shall be set to 'Completed', the exit time recorded, fee stored, and the slot freed (status = 'Available'). | High |
| FR-16 | The system shall prevent recording an exit time earlier than the entry time. | High |

### 3.5 Billing and Tariff

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-17 | The system shall maintain a tariff table with base rate, per-hour rate, and free minutes per vehicle type. | High |
| FR-18 | Fee calculation shall use only the tariff stored in the database; hardcoded rates are not allowed. | High |

### 3.6 Reporting

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-19 | The system shall export session, revenue, and vehicle reports to `.xlsx` with header formatting and auto column widths. | Medium |
| FR-20 | The system shall display a real-time utilization metric on the dashboard. | High |

### 3.7 Q03 Usability Features

| ID | Requirement | Feature |
|----|-------------|---------|
| FR-21 | The system shall provide a Dark Mode toggle in the sidebar that applies CSS variables to all UI elements and persists the choice across sessions. | Q03-1 |
| FR-22 | The system shall provide at least 5 colour palettes selectable from a dropdown with a live swatch preview, applicable to both the app and charts. | Q03-2 |
| FR-23 | The system shall display a Dashboard with KPI cards, occupancy chart by zone, revenue-by-day chart, and a recent activity table. | Q03-3 |
| FR-24 | The system shall provide Search Filters for vehicles and sessions (plate, owner, slot, status, type, date range) with a clear-filters button and result count. | Q03-4 |
| FR-25 | The system shall display a Calendar View with heat-coloured daily revenue cells, month navigation, and a day-detail table. | Q03-5 |

### 3.8 TQM Modules

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-26 | The system shall provide a Checksheet page to log defects and update their status. | High |
| FR-27 | The system shall provide an FMEA matrix with automatic RPN, sortable by highest RPN, with Excel export. | High |
| FR-28 | The system shall generate a Pareto chart from the defects table (bars by type, cumulative line, 80% reference). | High |
| FR-29 | The system shall generate a Fishbone (Ishikawa) diagram from defects grouped by four categories. | High |
| FR-30 | The system shall provide a PDCA log page to record cycle details and display a before-vs-after metric chart. | High |

---

## 4. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Usability | All error messages shall be user-friendly (no raw Python tracebacks). |
| NFR-02 | Usability | Entry processing (slot suggestion + session creation) shall complete in under 5 seconds on a local machine. |
| NFR-03 | Reliability | The system shall handle invalid inputs without crashing (Poka-Yoke validators). |
| NFR-04 | Reliability | Database constraints (UNIQUE, CHECK, FK) shall prevent invalid states. |
| NFR-05 | Maintainability | Every function shall have a short docstring. No hardcoded absolute paths. |
| NFR-06 | Testability | All business-logic functions shall be testable with pytest without launching the Streamlit UI. |
| NFR-07 | Performance | The dashboard shall load within 3 seconds with up to 1,000 session records. |
| NFR-08 | Portability | The system shall run on Windows, macOS, and Linux with only `pip install -r requirements.txt`. |
| NFR-09 | Security | The live database file (`parking.db`) shall not be committed to Git. |
| NFR-10 | Integrity | Demo seed rows shall be flagged with `is_demo = 1` and labelled 'DEMO' in the UI. |

---

## 5. Use-Case List

| Use Case | Actor | Description |
|----------|-------|-------------|
| UC-01 | Operator | Add a new parking slot |
| UC-02 | Operator | Register a new vehicle |
| UC-03 | Operator | Record vehicle entry and allocate slot |
| UC-04 | Operator | Record vehicle exit and compute fee |
| UC-05 | Operator | View and export session/revenue report |
| UC-06 | Operator | Switch dark/light mode |
| UC-07 | Operator | Select a colour theme |
| UC-08 | Operator | View Dashboard KPIs and charts |
| UC-09 | Operator | Search and filter sessions/vehicles |
| UC-10 | Operator | Navigate calendar and view daily entries |
| UC-11 | Operator | Log a defect in the Checksheet |
| UC-12 | Operator | View/edit FMEA matrix |
| UC-13 | Operator | Generate Pareto chart |
| UC-14 | Operator | Generate Fishbone diagram |
| UC-15 | Operator | Record a PDCA cycle |

---

## 6. Traceability Matrix

| Requirement | Module / File | Test |
|-------------|---------------|------|
| FR-01 to FR-05 | `modules/slots.py`, `ui_pages/pg_slots.py` | `tests/test_slots.py` |
| FR-06 to FR-09 | `modules/vehicles.py`, `ui_pages/pg_vehicles.py` | `tests/test_vehicles.py` |
| FR-10 to FR-12 | `modules/sessions.py`, `ui_pages/pg_entry.py` | `tests/test_sessions.py` |
| FR-13 to FR-16 | `modules/sessions.py`, `ui_pages/pg_exit.py` | `tests/test_sessions.py` |
| FR-17 to FR-18 | `modules/billing.py`, `config.py` | `tests/test_billing.py` |
| FR-19 to FR-20 | `modules/reports.py`, `features/dashboard.py` | `tests/test_reports.py` |
| FR-21 to FR-22 | `features/theme.py` | `tests/test_app_smoke.py` |
| FR-23 | `features/dashboard.py`, `ui_pages/pg_dashboard.py` | `tests/test_app_smoke.py` |
| FR-24 | `features/search_filters.py` | `tests/test_app_smoke.py` |
| FR-25 | `features/calendar_view.py` | `tests/test_app_smoke.py` |
| FR-26 to FR-30 | `tqm/*.py` | `tests/test_tqm.py` |
| NFR-01, NFR-03 | `modules/validation.py` | `tests/test_validation.py` |
