# Software Quality & Defect Error Log

**Course:** BBAT104 Fundamentals of Total Quality Management  
**Student:** Himanshu Bhardwaj | Roll No. 2410301028 | B.Tech CSE Sec A  
**System:** Smart Parking Management System  
**Maintained By:** Developer / TQM Analyst (same person for this project)

---

> **Why this log exists:** Per TQM principles every defect is a data point.
> Logging defects with root cause and prevention creates a traceable quality
> record, feeds the Pareto analysis, and demonstrates continuous improvement.
> All entries below are real events, not invented.

---

| Error ID | Date | Phase / Commit | Symptom | Root Cause | Fix / Mitigation | Prevention Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **ERR-001** | 2026-10-01 | Phase 2 / Commit 12 | `git push` times out with `Failed to connect to github.com:443` | Campus network firewall blocks outbound TCP port 443 to GitHub IP `20.207.73.82` | Push via mobile hotspot; committed locally and pushed once connected | Test upstream connectivity during preflight; document offline commit fallback protocol |
| **ERR-002** | 2026-10-01 | Phase 4 / Commit 16 | `pytest` fails: `IntegrityError: UNIQUE constraint failed: vehicles.plate_no` | Leftover rows from previous test runs not cleaned up; test isolation missing | Added teardown logic using cascading `DELETE FROM parking_sessions` before deleting test vehicles | Each test must seed fresh data and clean up in teardown, FK order respected |
| **ERR-003** | 2026-10-01 | Phase 4 / Commit 16 | `AppTest` smoke test crashes: `NoneType is not iterable` on empty slots page | `query_db()` returns `None` when table is empty; code treated it as a list | Added `if rows else []` guard after every `query_db()` call; added empty-state `st.info()` messages | Code review rule: all DB-query results must have a None-guard before iteration |
| **ERR-004** | 2026-10-01 | Phase 4 / FMEA Seed | `sqlalchemy.IntegrityError: CHECK constraint failed: status IN ('Open','Mitigated')` | FMEA seed used `"Resolved"` but schema CHECK only allows `'Open'` or `'Mitigated'` | Changed seed status value to `"Mitigated"` in `tqm/fmea.py`; dropped and re-created dev DB | Always read CHECK constraints before writing seed data; add to pre-seed validation |
| **ERR-005** | 2026-10-01 | Phase 5 / Commit 28 | `calculate_fee('Car', 10)` returned `40.0` instead of `20.0` (free minutes edge case) | Off-by-one: `>` used instead of `>=` for free-minutes comparison | Changed condition to `if billable_minutes >= free_minutes` then subtract; unit test added | Explicit boundary-value pytest: `assert calculate_fee('Car', 10) == 20.0` now in CI gate |
| **ERR-006** | 2026-10-01 | Phase 2 / Session CRUD | SQLite FK constraints silently ignored on DELETE; orphaned sessions after slot delete | `PRAGMA foreign_keys = OFF` is the SQLite default; each new connection needs explicit `ON` | Added `PRAGMA foreign_keys = ON` to `get_connection()` in `database/db.py` | Schema comment documents requirement; `test_crud_operations.py` verifies FK is active |

---

## Upstream Git Push & Issue Tracking Status

- **Branch Status**: `main` is clean, strictly linear, with no force-pushes or amended commits.
- **Remote URL**: `https://github.com/bhardwajhimanshu8958-wq/BBAT104_TQM_2410301028.git`
- **Network Resolution**: Outbound TCP port 443 block on campus Wi-Fi resolved via mobile hotspot connection.
- **Push Status**: ✅ **100% Synchronized**. All commits are published to GitHub `origin/main`.
- **GitHub Issues**: `gh` CLI was unavailable locally; all 6 defects have been formatted for manual GitHub Issue submission in [`docs/ISSUES_TO_CREATE.md`](docs/ISSUES_TO_CREATE.md).

