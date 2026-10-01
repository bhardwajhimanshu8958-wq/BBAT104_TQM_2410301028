# MASTER PROMPT — BBAT104 TQM PROJECT (Parking Management System, Q03)

Paste everything below this line into Antigravity as one message.

---

## 0. RUN MODE (edit before pasting)

```
RUN_UNTIL: Phase 6        # change to "Phase 2", "Phase 3" etc. to stop after that phase
GITHUB_REMOTE: <paste my GitHub repo URL here>
GIT_USER_NAME: Himanshu Bhardwaj
GIT_USER_EMAIL: <my GitHub email>
```

Work autonomously. Do not ask for confirmation between commits. Stop only when you hit a real blocker (missing credentials, failing push, ambiguous requirement) or when `RUN_UNTIL` is reached. At the end of every phase print a short checkpoint: commits made so far, what works, what is next.

## 1. ROLE AND MISSION

You are a senior Python engineer and a Total Quality Management (TQM) practitioner. Build a complete university course project, step by step, and commit every step to Git yourself.

Course: BBAT104 Fundamentals of TQM, Session 2026-27. The project is an integrated software development plus quality audit task. Marks: 70 raw marks. The application is only about 25 percent of the weight. The TQM artefacts, development records and GitHub health carry the rest. So keep the application simple, correct and demonstrable, and make the TQM implementation strong and traceable to real data from the app.

## 2. PROJECT FACTS (fixed, do not change)

- Student: Himanshu Bhardwaj, Roll No. 2410301028, B.Tech CSE Sec A
- Baseline system (roll number ends in 8): **Parking Management System**. Core TQM goal: minimize entry queues and maximize space utilization.
- Assigned quality goal: **Q03: Improve Usability**. Implement ALL FIVE features: **Dark Mode, Custom Themes, Dashboard Overview, Search Filters, Calendar**.
- GitHub repo name must be exactly `BBAT104_TQM_2410301028` (public). Root folder uses the same name.
- Stack (fixed): Python 3.x, **Streamlit** (UI), **SQLite3** (storage), **pandas**, **openpyxl** (Excel), **matplotlib** and **seaborn** (SQC charts), **pytest** (tests). No other frameworks. Everything must run locally with `pip install -r requirements.txt` then `streamlit run app.py`.

## 3. GIT AUTOMATION PROTOCOL (mandatory)

Preflight, before commit 1:
1. Check `git --version`, `python --version`, `pip --version`. Report any that are missing.
2. Create the folder `BBAT104_TQM_2410301028`, run `git init -b main`, set `git config user.name` and `user.email` from Section 0, and add `origin` from `GITHUB_REMOTE`. If the remote is a placeholder, work locally and tell me at the end of Phase 1 to add it.
3. Create a Python virtual environment `.venv` (gitignored).

For every numbered commit in Section 9:
1. Do only that commit's work. One commit equals one focused step. Never batch two commits together.
2. Run its quality gate (Section 10).
3. Stage only the relevant files: `git add <files>` (never blindly `git add .` after commit 1).
4. Commit with the exact message given in Section 9.
5. Run `git push origin main`. If the push fails, keep committing locally, and tell me clearly what failed and how to fix it.
6. Run `git log --oneline -1` and print the result so I can see progress.

Hard rules:
- Never use `--amend`, `rebase`, `reset --hard`, `push --force` or squash. History must stay linear and honest.
- Never fake or backdate timestamps (no `GIT_AUTHOR_DATE`, no `--date`). Commit dates must be real.
- Never commit secrets, `.venv`, `__pycache__`, or the live `parking.db` (commit `schema.sql` and `seed.py` instead).
- At the end, run `git log --oneline | wc -l` and confirm there are at least 34 commits.

## 4. ERROR LOG AND ISSUES (mandatory, professor requirement)

- Maintain `docs/ERROR_LOG.md`. Every time something fails during development (exception, failed test, wrong output, push error), append a row: ID, date, phase/commit, symptom, root cause, fix, prevention. Include that log update in the same commit that fixes the problem.
- If `gh` (GitHub CLI) is installed and authenticated, create a GitHub Issue for each real bug and close it with a commit message that references it (`fixes #N`). If `gh` is not available, write the issues to `docs/ISSUES_TO_CREATE.md` in a ready-to-paste format and tell me.

## 5. REPOSITORY STRUCTURE

```
BBAT104_TQM_2410301028/
├── app.py                     # entry point, st.navigation with st.Page (Streamlit >= 1.36)
├── config.py                  # constants: DB path, tariffs, defect categories, theme palettes
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/config.toml
├── database/
│   ├── db.py                  # connection helper, context manager, init_db()
│   ├── schema.sql
│   └── seed.py                # demo data, clearly flagged as DEMO
├── modules/
│   ├── slots.py               # slot CRUD
│   ├── vehicles.py            # vehicle CRUD
│   ├── sessions.py            # entry / exit / allocation
│   ├── billing.py             # tariff + fee calculation
│   ├── validation.py          # Poka-Yoke validators
│   └── reports.py             # pandas + openpyxl Excel export
├── features/                  # the 5 Q03 features
│   ├── theme.py               # dark mode + custom themes
│   ├── dashboard.py
│   ├── search_filters.py
│   └── calendar_view.py
├── tqm/
│   ├── checksheet.py          # defect log / checksheet (SQLite backed)
│   ├── fmea.py                # FMEA with RPN
│   ├── pareto.py              # Pareto generator (matplotlib)
│   ├── fishbone.py            # Ishikawa generator (matplotlib)
│   └── pdca.py                # PDCA cycle log
├── ui_pages/                  # one file per Streamlit page
├── tests/                     # pytest + streamlit.testing.v1.AppTest smoke tests
├── docs/
│   ├── SRS.md
│   ├── ARCHITECTURE.md        # Mermaid flowchart (also rendered to PNG)
│   ├── CTQ_TREE.md
│   ├── SIPOC.md
│   ├── FMEA.md
│   ├── PDCA_LOG.md
│   ├── USER_MANUAL.md
│   ├── ERROR_LOG.md
│   └── screenshots/
└── exports/                   # generated Excel/PNG outputs (kept with .gitkeep)
```

## 6. DATABASE SCHEMA (SQLite, enforce with constraints)

- `slots(slot_id PK, slot_code TEXT UNIQUE NOT NULL, zone TEXT, slot_type TEXT CHECK IN ('Car','Bike','EV','Disabled'), status TEXT CHECK IN ('Available','Occupied','Maintenance') DEFAULT 'Available')`
- `vehicles(vehicle_id PK, plate_no TEXT UNIQUE NOT NULL, owner_name TEXT NOT NULL, phone TEXT, vehicle_type TEXT CHECK IN ('Car','Bike','EV'), created_at TEXT)`
- `tariff(vehicle_type PK, base_rate REAL, per_hour_rate REAL, free_minutes INTEGER)`
- `parking_sessions(session_id PK, vehicle_id FK, slot_id FK, entry_time TEXT, exit_time TEXT NULL, fee REAL NULL, status TEXT CHECK IN ('Active','Completed'))`
- `settings(key PK, value)` stores the chosen theme mode and palette
- `defects(defect_id PK, date_found, module, description, fishbone_category CHECK IN ('People','Process','Software Code','Infrastructure'), defect_type, severity INTEGER 1-10, status CHECK IN ('Open','In Progress','Resolved'), resolution, is_demo INTEGER DEFAULT 0)`
- `fmea(fmea_id PK, process_step, failure_mode, effect, cause, severity INTEGER, occurrence INTEGER, detection INTEGER, rpn INTEGER, mitigation, status)`; RPN = S x O x D, computed in code and in SQL view
- `pdca(pdca_id PK, cycle_no, plan, do_action, check_result, act_decision, metric_name, before_value, after_value, date)`

## 7. APPLICATION FEATURE SPEC

### 7.1 Baseline modules (Review 2: CRUD must work with zero crashes)
- **Slots:** create, read, update, delete. Cannot delete an occupied slot.
- **Vehicles:** create, read, update, delete. Plate number unique.
- **Entry:** register a vehicle entering, auto-suggest the first available slot of the matching type (this supports the goal "minimize entry queues"), mark the slot Occupied, record entry time.
- **Exit:** compute the fee from the tariff (free minutes, base rate, per-hour, rounded up per hour), mark session Completed, free the slot.
- **Utilization metric:** occupied slots / total non-maintenance slots (supports "maximize space utilization").
- **Reports:** export sessions, revenue and vehicles to `.xlsx` using pandas + openpyxl, with header formatting and auto column width.
- **Poka-Yoke validation** (`validation.py`): plate format regex for Indian plates (e.g. `UK07AB1234`), 10-digit phone, non-empty names, no exit before entry, no double entry for an already parked vehicle. Show friendly errors, never raw tracebacks.

### 7.2 Q03 features (all five, each visible in the UI)
1. **Dark Mode:** a sidebar toggle. Apply by injecting CSS through `st.markdown(..., unsafe_allow_html=True)` using CSS variables (background, text, cards, inputs, tables). Persist in `settings`. Do not rely on private Streamlit config APIs.
2. **Custom Themes:** at least 5 palettes (for example Ocean, Forest, Sunset, Royal, Slate) selectable from a dropdown with a live preview swatch. Works together with dark/light mode and also colours matplotlib charts. Persist the choice.
3. **Dashboard Overview:** KPI cards (total slots, occupied, available, utilization %, today's revenue, vehicles today), an occupancy chart by zone, a revenue-by-day chart, and a recent activity table.
4. **Search Filters:** search vehicles and sessions by plate, owner, slot, status, vehicle type, and date range, with a clear-filters button and result count.
5. **Calendar:** a month view built with Python's `calendar` module and pandas that shows entries and revenue per day (heat-coloured cells), month navigation, and a day-detail table when a date is chosen.

### 7.3 TQM modules inside the app
- **Checksheet page:** a form to log defects (writes to `defects`), a filterable table, and status updates.
- **FMEA page:** editable matrix with automatic RPN, sort by highest RPN, Excel export.
- **Pareto page:** builds the chart from the `defects` table: bars by defect type sorted descending, cumulative-percentage line, 80 percent reference line.
- **Fishbone page:** generates the Ishikawa diagram from `defects` grouped by the four categories (People, Process, Software Code, Infrastructure).
- **PDCA page:** log cycles with before/after metrics and a simple before-vs-after chart.

## 8. TQM ARTEFACT SPECS (written documents)

- **SRS (`docs/SRS.md`):** purpose, scope, in/out of scope, stakeholders, functional requirements (numbered FR-1...), non-functional requirements (usability, reliability, performance), assumptions, constraints, use-case list, traceability table mapping requirements to modules and to the five Q03 features.
- **Architecture flowchart (`docs/ARCHITECTURE.md`):** Mermaid flowchart of the vehicle entry-to-exit process plus a layered architecture diagram (UI, modules, database). Also export a PNG.
- **CTQ tree (`docs/CTQ_TREE.md`):** Need -> Driver -> CTQ with measurable targets (for example, entry processing under 30 seconds, zero duplicate plates, utilization above 80 percent).
- **SIPOC (`docs/SIPOC.md`):** Suppliers, Inputs, Process (5 to 7 steps), Outputs, Customers for the parking process.
- **FMEA (`docs/FMEA.md`):** at least 12 failure modes across entry, exit, billing, slot allocation, database and UI. Severity, Occurrence, Detection on a 1-10 scale with a stated rating rubric, RPN, top-5 risks, mitigation actions, and re-scored RPN after mitigation.
- **Pareto and Fishbone:** generated only by the Python code in `tqm/`, saved as PNG in `docs/` and `exports/`, and embedded in the README.
- **PDCA log (`docs/PDCA_LOG.md`):** at least 2 complete cycles: Plan (target defect and metric), Do (change made, linked to a commit), Check (metric after), Act (standardize or next cycle).

## 9. COMMIT PLAN (34 commits, execute in this exact order)

### Phase 1: Setup and SRS (Review 1)
1. `chore: initialize repository with README and .gitignore`
2. `docs: add project scope, assignment details and Q03 feature list`
3. `docs: add Software Requirements Specification (SRS)`
4. `docs: add system architecture flowchart`
5. `docs: add CTQ tree and CTQ parameters`
6. `chore: add project structure, requirements.txt, config and Streamlit config`

### Phase 2: Base system and CRUD (Review 2, part 1)
7. `feat(db): add SQLite schema and connection layer`
8. `feat(db): add demo seed script`
9. `feat(slots): add parking slot CRUD`
10. `feat(vehicles): add vehicle CRUD`
11. `feat(entry): add vehicle entry with automatic slot suggestion`
12. `feat(exit): add vehicle exit and fee calculation`
13. `feat(app): add main navigation and home page`
14. `feat(validation): add Poka-Yoke input validation`
15. `feat(reports): add Excel export with pandas and openpyxl`
16. `test: add unit tests for CRUD, entry/exit and billing`

### Phase 3: Q03 Improve Usability features (Review 2, part 2)
17. `feat(q03): add dark mode toggle`
18. `feat(q03): add custom themes with live preview`
19. `feat(q03): add dashboard overview`
20. `feat(q03): add search filters`
21. `feat(q03): add calendar view`
22. `docs: add screenshots and Review 2 progress notes to README`

### Phase 4: Risk audit (Review 3)
23. `feat(tqm): add defect checksheet module`
24. `docs: add SIPOC diagram`
25. `feat(tqm): add FMEA module with RPN calculation`
26. `docs: add FMEA matrix, top risks and mitigation plan`

### Phase 5: SQC and continuous improvement (Review 4)
27. `feat(tqm): add Pareto chart generator`
28. `feat(tqm): add Fishbone diagram generator`
29. `feat(tqm): add PDCA cycle log module`
30. `fix: implement PDCA cycle 1 improvements for top defects`
31. `docs: record PDCA cycles with before and after metrics`

### Phase 6: Documentation and release (Final demo, GitHub health)
32. `docs: add user manual`
33. `docs: finalize README with setup, architecture and TQM artefacts`
34. `chore: release v1.0 with final cleanup and error log`

Rules for the plan: if a step naturally produces a real bug fix, make it its own extra commit (`fix(...)`) rather than hiding it inside another commit. More than 34 commits is fine. Fewer is not.

## 10. QUALITY GATES (run before every commit)

- `python -m compileall .` passes.
- `pytest -q` passes (from commit 16 onward).
- From commit 13 onward, run a Streamlit smoke test using `streamlit.testing.v1.AppTest` and confirm there is no exception in the page you changed.
- No debug prints, no commented-out dead code, no hardcoded absolute paths.
- Every function has a short docstring. Comments explain why, not what.

## 11. INTEGRITY RULES (very important)

- **Defect data must be real.** Log only defects actually found while building and testing (failed tests, validation gaps, UI bugs, push errors). If a chart needs more data, run a documented test session (a written list of test cases across modules) and log what actually fails. Any placeholder demo rows must have `is_demo = 1` and be labelled DEMO everywhere they appear, so I can replace them with my own observations before submission. Do not invent a history that did not happen.
- Do not copy code from any existing repository. Write everything fresh.
- FMEA ratings must be justified by the stated rubric, not random.
- Everything must be explainable by me in a viva: keep the code simple and readable, and put a short "why this tool was chosen" note in each TQM document (why Pareto, why Fishbone, why FMEA, why PDCA).

## 12. FINAL ACCEPTANCE CHECKLIST (verify before declaring done)

- [ ] Repo named `BBAT104_TQM_2410301028`, at least 34 commits, linear history, all pushed
- [ ] All CRUD modules work; entry, exit and billing correct; no crashes on bad input
- [ ] All 5 Q03 features work and are visible in the UI (dark mode, custom themes, dashboard overview, search filters, calendar)
- [ ] SRS, architecture flowchart, CTQ tree, SIPOC, FMEA (with RPN), Pareto, Fishbone, checksheet, PDCA log all present
- [ ] `docs/ERROR_LOG.md` filled with real entries; GitHub Issues created (or `ISSUES_TO_CREATE.md`)
- [ ] README has setup steps, screenshots, architecture, feature list, TQM artefact links; `docs/USER_MANUAL.md` present
- [ ] `streamlit run app.py` works from a fresh clone with only `pip install -r requirements.txt`

## 13. START

Begin now: run the preflight in Section 3, then execute commit 1, and continue in order until `RUN_UNTIL`.
