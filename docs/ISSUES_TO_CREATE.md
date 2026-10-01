# GitHub Issues to Create (Manual Entry Guide)

**Course:** BBAT104 Fundamentals of Total Quality Management  
**Student:** Himanshu Bhardwaj | Roll No. 2410301028 | B.Tech CSE Sec A  
**Repository:** `bhardwajhimanshu8958-wq/BBAT104_TQM_2410301028`  

> **Note:** The `gh` CLI was not detected on the local development environment.  
> As instructed by the course requirements, the following defect records are pre-formatted for manual creation via the GitHub Issues web UI.

---

### Issue #1: `[BUG] Git push timeouts due to upstream port 443 network restriction`
- **Labels:** `infrastructure`, `network`, `wontfix-external`
- **Severity:** High
- **Description:**
  ```markdown
  ### Symptom
  `git push origin main` failed with fatal error: `Failed to connect to github.com port 443: Timed out`.

  ### Root Cause
  Campus institutional Wi-Fi gateway blocked outbound TCP 443 traffic to GitHub IP addresses.

  ### Resolution
  Switched to cellular mobile hotspot connection; queued commits were pushed cleanly with linear history.

  ### Prevention Strategy
  Verify remote network connectivity during preflight checks; commit locally and push in batches when stable uplink is available.
  ```

---

### Issue #2: `[BUG] Unit test teardown failure: UNIQUE constraint failed on vehicle plate number`
- **Labels:** `testing`, `database`, `bug`
- **Severity:** Medium
- **Description:**
  ```markdown
  ### Symptom
  Repeated execution of `pytest` caused `sqlite3.IntegrityError: UNIQUE constraint failed: vehicles.plate_no`.

  ### Root Cause
  Previous test iterations left persistent vehicle records in test fixture database due to missing teardown isolation.

  ### Resolution
  Implemented clean teardown routines deleting child `parking_sessions` followed by test `vehicles`.

  ### Prevention Strategy
  Ensure test isolation in all pytest fixtures; enforce deterministic teardown logic.
  ```

---

### Issue #3: `[BUG] Unhandled NoneType exception on empty database query results`
- **Labels:** `ui`, `bug`, `poka-yoke`
- **Severity:** High
- **Description:**
  ```markdown
  ### Symptom
  UI pages crashed on fresh installation with `TypeError: 'NoneType' object is not iterable` when tables contained 0 rows.

  ### Root Cause
  `query_db()` returned `None` or empty list without caller null-checks.

  ### Resolution
  Added defensive `rows = query_db(...) or []` guards across all Streamlit page views and added informative `st.info()` empty-state notices.

  ### Prevention Strategy
  Code quality rule: Never iterate directly over query results without fallback defaults.
  ```

---

### Issue #4: `[BUG] FMEA seed data rejected by SQLite table CHECK constraint`
- **Labels:** `database`, `tqm`, `bug`
- **Severity:** Medium
- **Description:**
  ```markdown
  ### Symptom
  Executing `database/seed.py` failed with `sqlite3.IntegrityError: CHECK constraint failed: status IN ('Open','Mitigated')`.

  ### Root Cause
  Seed script inserted status `"Resolved"`, which was not in the schema CHECK constraint whitelist (`'Open'`, `'Mitigated'`).

  ### Resolution
  Updated FMEA seed records to use `"Mitigated"` status matching the schema constraint.

  ### Prevention Strategy
  Cross-validate seed fixtures directly against `database/schema.sql` definitions.
  ```

---

### Issue #5: `[BUG] Tariff calculation error: Short stay duration misbilled outside free grace tier`
- **Labels:** `billing`, `calculation`, `critical`
- **Severity:** High
- **Description:**
  ```markdown
  ### Symptom
  `calculate_fee('Car', 10)` returned Rs 40.0 instead of base charge Rs 20.0 during grace tier evaluation.

  ### Root Cause
  Boundary comparison used strict equality/inversion logic instead of `max(0, stay_minutes - free_minutes)`.

  ### Resolution
  Refactored billing mathematics to correctly deduct free tier minutes and enforce floor bounds. Added unit test `test_billing_calculation()`.

  ### Prevention Strategy
  Boundary value analysis (BVA) applied to all financial calculations in pytest suite.
  ```

---

### Issue #6: `[BUG] Foreign key constraints not enforced by default in SQLite connection`
- **Labels:** `database`, `integrity`, `bug`
- **Severity:** High
- **Description:**
  ```markdown
  ### Symptom
  Deleting a slot or vehicle was not preventing orphaned child sessions when executed via raw cursor.

  ### Root Cause
  SQLite requires `PRAGMA foreign_keys = ON;` to be explicitly executed per database connection.

  ### Resolution
  Added automatic PRAGMA activation inside `get_connection()` in `database/db.py`.

  ### Prevention Strategy
  Centralized connection factory ensures every connection inherits referential integrity rules.
  ```
