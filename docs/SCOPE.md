# Project Scope, Assignment Details, and Q03 Feature List

## Assignment Details

| Field | Value |
|-------|-------|
| Course | BBAT104 — Fundamentals of Total Quality Management |
| Session | 2026-27 |
| Student | Himanshu Bhardwaj |
| Roll No | 2410301028 |
| Section | B.Tech CSE Sec A |
| Project | Q03 — Parking Management System |
| Total Marks | 70 (Application ≈ 25%, TQM artefacts + GitHub health ≈ 75%) |

---

## Project Scope

### Baseline System
A **Parking Management System** with the following core TQM goals:
- **Minimize entry queues** — auto-suggest the first available slot on vehicle entry.
- **Maximize space utilization** — real-time utilization metric (Occupied ÷ Total non-maintenance slots).

### In Scope
- Parking slot CRUD (Create, Read, Update, Delete)
- Vehicle registration CRUD
- Vehicle entry and exit with automatic slot allocation
- Fee calculation based on configurable tariff (free minutes, base rate, per-hour rate)
- Poka-Yoke (mistake-proofing) input validation
- Excel export of sessions, revenue and vehicle reports
- Five Q03 usability features (see below)
- TQM modules: Checksheet, FMEA, Pareto chart, Fishbone diagram, PDCA log
- Complete TQM documentation: SRS, Architecture, CTQ Tree, SIPOC, FMEA, PDCA Log, User Manual, Error Log

### Out of Scope
- Online/web payment gateway integration
- Hardware integration (barriers, sensors, cameras)
- Multi-location or multi-floor parking across different sites
- Mobile application
- Real-time SMS/email notifications

---

## Stakeholders

| Stakeholder | Role |
|-------------|------|
| Parking Operator | Primary user: manages slots, vehicles, billing |
| Vehicle Owner | Enters/exits the parking facility |
| Course Evaluator | Examines TQM artefacts and GitHub history |
| Student Developer | Builds and quality-audits the system |

---

## Q03 Feature List: Improve Usability

The assigned quality goal is **Q03: Improve Usability**. All five features below are mandatory and must be visible in the running UI.

| # | Feature | Description | UI Location |
|---|---------|-------------|-------------|
| 1 | **Dark Mode** | Sidebar toggle to switch between light and dark colour schemes. CSS injected via `st.markdown`. Choice persisted in the `settings` table. | Sidebar |
| 2 | **Custom Themes** | 5 palettes — Ocean, Forest, Sunset, Royal, Slate — selectable from a dropdown with a live colour swatch. Applies to both the app and matplotlib charts. Persisted in `settings`. | Sidebar / Settings page |
| 3 | **Dashboard Overview** | KPI cards (total slots, occupied, available, utilization %, today's revenue, vehicles today), occupancy chart by zone, revenue-by-day line chart, recent activity table. | Dashboard page |
| 4 | **Search Filters** | Filter vehicles and sessions by plate number, owner name, slot code, session status, vehicle type, and date range. Includes a "Clear Filters" button and a result count. | Vehicles / Sessions pages |
| 5 | **Calendar View** | A month-view calendar built with Python's `calendar` module and pandas. Cells are heat-coloured by daily revenue. Month navigation (Previous/Next). Click a date to see a day-detail entry/exit table. | Calendar page |

---

## Traceability Summary

| Requirement Area | Module / File | Q03 Feature |
|-----------------|---------------|-------------|
| Slot CRUD | `modules/slots.py` | — |
| Vehicle CRUD | `modules/vehicles.py` | — |
| Entry / Exit | `modules/sessions.py` | — |
| Billing | `modules/billing.py` | — |
| Poka-Yoke | `modules/validation.py` | — |
| Reports | `modules/reports.py` | — |
| Dark Mode | `features/theme.py` | Q03-1 |
| Custom Themes | `features/theme.py` | Q03-2 |
| Dashboard | `features/dashboard.py` | Q03-3 |
| Search Filters | `features/search_filters.py` | Q03-4 |
| Calendar | `features/calendar_view.py` | Q03-5 |
| TQM Checksheet | `tqm/checksheet.py` | — |
| TQM FMEA | `tqm/fmea.py` | — |
| TQM Pareto | `tqm/pareto.py` | — |
| TQM Fishbone | `tqm/fishbone.py` | — |
| TQM PDCA | `tqm/pdca.py` | — |
