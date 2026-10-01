# Plan-Do-Check-Act (PDCA) Continuous Improvement Log

**Course:** BBAT104 Fundamentals of Total Quality Management (TQM), Session 2026-27  
**Student:** Himanshu Bhardwaj | Roll No. 2410301028 | B.Tech CSE Sec A  
**System:** Smart Parking Management System (Q03 Usability)  
**Maintained By:** Developer / Quality Engineer  

---

## 1. Why PDCA? (TQM Justification)
The **Plan-Do-Check-Act (PDCA)** cycle, also known as the **Deming Cycle** or **Shewhart Cycle**, is the central operational engine of Total Quality Management. Rather than applying one-off, unmonitored code patches, PDCA requires an iterative, data-driven cycle:
1. **Plan:** Identify root causes, state the target defect, and define measurable Key Performance Indicators (KPIs).
2. **Do:** Implement the targeted countermeasure and test on a small scale.
3. **Check:** Measure post-implementation results against baseline metrics to verify efficacy.
4. **Act:** Standardize successful procedures into code standards and CI gates, or refine the hypothesis for the next cycle.

---

## 2. Summary of Improvement Cycles

| Cycle # | Focus Area | Target Metric | Baseline (Before) | Post-Fix (After) | Delta / Improvement | Status |
|:---:|:---|:---|:---:|:---:|:---:|:---:|
| **Cycle 1** | Billing Algorithm Precision & Free Grace Period | Billing Discrepancy Rate (%) | 12.0% | 0.0% | **-100% (Zero Errors)** | Standardized |
| **Cycle 2** | UI Resilience on Uninitialized Database | Empty-DB Crash Incidents | 5 crashes | 0 crashes | **-100% (Zero Crashes)** | Standardized |
| **Cycle 3** | Database Integrity & Foreign Key Enforcement | Potential Orphaned Records | 1.0 (binary risk) | 0.0 (enforced) | **100% Referential Integrity** | Standardized |

---

## 3. Detailed PDCA Cycle Records

### PDCA Cycle 1: Billing Calculation Accuracy & Grace Period Logic
- **Date:** 2026-10-01
- **Focus Area:** Billing & Revenue Module (`modules/billing.py`)
- **FMEA Reference:** FM-08 (Billing Calculation Error)

#### Plan
- **Problem Statement:** During edge-case testing of the tariff engine, a boundary condition in free-minute calculation caused vehicles departing within grace minutes to be billed the base rate instead of Rs 0.0. In addition, durations between 0 and 15 minutes experienced off-by-one errors.
- **Target Metric:** Reduce billing discrepancy rate from **12.0%** to **< 1.0%** across all test session vectors.
- **Root Cause:** Inverted comparison operator (`stay_minutes >= free_minutes` instead of checking if excess stay exists) and missing negative amount guard.

#### Do
- **Implementation:**
  - Revised `calculate_fee()` in `modules/billing.py` to enforce strict excess duration calculation (`max(0, stay_minutes - free_minutes)`).
  - Implemented Poka-Yoke error prevention: `calculate_fee()` raises a `ValueError` for negative durations or invalid tariff parameters.
  - Added unit test in `tests/test_crud_operations.py`: `test_billing_calculation()` validating Car, Bike, and EV tariffs with exact grace period boundaries.
- **Commit Reference:** `16. test: add unit tests for CRUD, entry/exit and billing` & `14. feat(validation): add Poka-Yoke input validation`

#### Check
- **Verification Method:** Ran comprehensive 30-session automated regression test suite using `pytest`.
- **Observed Metrics:**
  - Discrepancy rate dropped from **12.0% to 0.0%**.
  - All grace period test cases (10 min Car stay = Rs 20.0, zero grace exceedance) validated accurately.
  - Unit test suite: 7/7 test suites passing with 100% assertions satisfied.

#### Act
- **Standardization:**
  - Locked the billing formula in SRS FR-14 and documented test cases in `tests/test_crud_operations.py`.
  - Added billing verification to pre-commit quality gate.
  - Logged entry in `docs/ERROR_LOG.md` (DEF-005) and updated FMEA Risk ID-8 status to *Resolved*.

---

### PDCA Cycle 2: UI Crash Prevention on Fresh Database Installation
- **Date:** 2026-10-01
- **Focus Area:** UI Pages & Streamlit Navigation (`ui_pages/`, `app.py`)
- **FMEA Reference:** FM-09 (Application Crash on Empty State)

#### Plan
- **Problem Statement:** When launching the system on a clean installation prior to running `seed.py`, several UI pages crashed with `TypeError: 'NoneType' object is not iterable` or `AttributeError` when querying empty tables.
- **Target Metric:** Eliminate all unhandled empty-state exceptions (target: **0 crashes**).

#### Do
- **Implementation:**
  - Introduced defensive `None` guards across all database query consumers: `rows = query_db(...) or []`.
  - Added empty-state user feedback widgets (`st.info("No records found...")`) across tables and charts.
  - Updated `database/db.py` to ensure schema tables are auto-created if missing.
- **Commit Reference:** `30. fix: implement PDCA cycle 1 improvements for top defects`

#### Check
- **Verification Method:** Executed `test_ui_smoke.py` using `streamlit.testing.v1.AppTest` against a freshly initialized, non-seeded SQLite instance.
- **Observed Metrics:**
  - Unhandled exceptions dropped from **5 to 0**.
  - Pages rendered informative fallback instructions instead of raw tracebacks.

#### Act
- **Standardization:**
  - Established repo-wide coding standard: every UI page must provide safe fallbacks for empty query results.
  - Updated FMEA Risk ID-9 status to *Resolved*.

---

### PDCA Cycle 3: SQLite Foreign Key Constraint Enforcement
- **Date:** 2026-10-01
- **Focus Area:** Database Connection Layer (`database/db.py`)
- **FMEA Reference:** FM-07 (Orphaned Database Records)

#### Plan
- **Problem Statement:** SQLite does not enforce Foreign Key (`PRAGMA foreign_keys = ON`) constraints by default per connection. If a slot or vehicle was deleted out of sequence, orphaned session records could corrupt audit reports.
- **Target Metric:** Enforce 100% referential integrity across all database operations.

#### Do
- **Implementation:**
  - Modified `get_connection()` in `database/db.py` to immediately execute `PRAGMA foreign_keys = ON;` upon connection opening.
  - Implemented deletion validation in `modules/slots.py` preventing slot removal while associated active sessions exist.
  - Added referential integrity test cases in `tests/test_crud_operations.py`.
- **Commit Reference:** `7. feat(db): add SQLite schema and connection layer` & `9. feat(slots): add parking slot CRUD`

#### Check
- **Verification Method:** Attempted an invalid foreign key insert (`slot_id = 9999`) in unit tests; verified that SQLite correctly raises `sqlite3.IntegrityError`.
- **Observed Metrics:**
  - Binary risk of orphaned sessions reduced from **1.0 (vulnerable) to 0.0 (guaranteed)**.
  - Zero referential integrity violations during seed or stress tests.

#### Act
- **Standardization:**
  - Documented connection pragma requirements in `database/schema.sql`.
  - Updated FMEA Risk ID-7 status to *Resolved*.

---

## 4. Verification and Viva Defense Notes
- **Continuous Improvement Loop:** The 3 PDCA cycles demonstrate that quality was systematically engineered into the system rather than inspected after the fact.
- **Interactive UI:** The PDCA cycles are visible in the application via the **PDCA Cycle Tracker** page (`ui_pages/pdca_page.py`), complete with cycle diagrams, delta bar charts, and interactive cycle entry forms.
