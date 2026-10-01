# User Manual — Smart Parking Management System
## BBAT104 TQM Project

**Student:** Himanshu Bhardwaj | Roll No. 2410301028 | B.Tech CSE Sec A  
**Stack:** Python 3.x · Streamlit · SQLite3 · pandas · openpyxl · matplotlib  
**Version:** 1.0 (Review 3 / Final Submission)

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Navigation Overview](#2-navigation-overview)
3. [Operations — Parking Module](#3-operations--parking-module)
   - 3.1 Entry & Exit
   - 3.2 Parking Slot Manager
   - 3.3 Vehicle Registry
4. [Q03 Usability Suite](#4-q03-usability-suite)
   - 4.1 Dark Mode
   - 4.2 Custom Themes
   - 4.3 Executive Dashboard
   - 4.4 Search & Filter Records
   - 4.5 Monthly Calendar View
5. [TQM Quality Control Tools](#5-tqm-quality-control-tools)
   - 5.1 Defect Checksheet
   - 5.2 FMEA Risk Audit
   - 5.3 Pareto 80/20 Analysis
   - 5.4 Ishikawa Fishbone Diagram
   - 5.5 PDCA Continuous Improvement
   - 5.6 SPC Control Chart
   - 5.7 TQM Summary Report
6. [Excel Reports & Export](#6-excel-reports--export)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Quick Start

### Prerequisites
- Python 3.10 or higher
- pip (bundled with Python)

### Installation
```bash
# 1. Clone the repository
git clone https://github.com/bhardwajhimanshu8958-wq/BBAT104_TQM_2410301028.git
cd BBAT104_TQM_2410301028

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Launch the application
streamlit run app.py
```

The browser opens automatically at **http://localhost:8501**.  
The database (`parking.db`) and demo data are created automatically on the first run — no manual setup needed.

---

## 2. Navigation Overview

The sidebar contains three grouped sections:

| Section | Pages |
|:---|:---|
| **Operations** | Home & Overview, Entry & Exit, Slot Manager, Vehicle Registry |
| **Q03 Usability Suite** | Executive Dashboard, Search & Filter, Calendar View, Excel Reports |
| **TQM Quality Control** | Defect Checksheet, FMEA, Pareto, Fishbone, PDCA, Control Chart, TQM Report |

The **Theme Selector** (top of sidebar) lets you switch between Dark/Light mode and colour palettes at any time.

---

## 3. Operations — Parking Module

### 3.1 Entry & Exit Operations

**Registering a Vehicle Entry:**
1. Select the vehicle from the **Registered Vehicle** dropdown (or add it in Vehicle Registry first).
2. The system auto-suggests the **first available slot** that matches the vehicle type (Car/Bike/EV). You may change the slot.
3. Click **Record Entry**. The slot status changes to `Occupied` immediately.

> **Poka-Yoke Guard:** If the vehicle already has an active session, entry is blocked with a friendly error message.

**Processing a Vehicle Exit:**
1. Select the active session from the dropdown — only currently parked vehicles appear.
2. The system computes the fee automatically:
   - **Free grace period** (e.g., 10 min for Cars) — no charge.
   - **Base rate** for the first billable hour (partial hour charged as full).
   - **Per-hour rate** for each subsequent hour.
3. Review the fee summary and click **Process Exit**. The slot is freed and the session marked `Completed`.

> **Receipt:** A formatted receipt is shown on-screen after exit with entry time, exit time, duration, and fee breakdown.

---

### 3.2 Parking Slot Manager

| Action | How |
|:---|:---|
| **Add Slot** | Fill Slot Code (e.g., `A-01`), Zone, Type (Car/Bike/EV/Disabled) → Save |
| **Edit Slot** | Expand the slot row → edit fields → Update |
| **Delete Slot** | Click Delete. **Blocked** if the slot is currently `Occupied`. |
| **View Status** | Live colour-coded table: 🟢 Available · 🔴 Occupied · 🔧 Maintenance |

---

### 3.3 Vehicle Registry

| Action | How |
|:---|:---|
| **Register Vehicle** | Enter plate number (format: `XX99XX9999`), owner name, phone, type |
| **Edit Vehicle** | Expand vehicle row → edit → Save |
| **Delete Vehicle** | Removes the vehicle record (only if no active session exists) |

> **Poka-Yoke:** Plate format is validated against the Indian registration regex. Duplicate plates are rejected. Phone must be exactly 10 digits.

---

## 4. Q03 Usability Suite

### 4.1 Dark Mode

Toggle **Dark Mode** from the top of the sidebar. The switch is persistent — your preference is stored in the database and restored on the next launch.

**What changes in Dark Mode:**
- Background: deep navy (`#0d1b2a`)
- Cards, inputs, tables: semi-transparent dark panels
- All matplotlib charts: dark background (`#1b2a3b`) with light axis labels

---

### 4.2 Custom Themes

Select a **Colour Palette** from the sidebar dropdown. Five palettes are available:

| Palette | Primary Colour | Character |
|:---|:---|:---|
| Ocean | Cyan `#00b4d8` | Cool & professional |
| Forest | Teal `#2a9d8f` | Calm & sustainable |
| Sunset | Coral `#e76f51` | Warm & energetic |
| Royal | Purple `#7b2cbf` | Premium & elegant |
| Slate | Steel `#457b9d` | Neutral & corporate |

The chosen palette applies instantly to all UI accents and all matplotlib/seaborn charts.

---

### 4.3 Executive Dashboard

Real-time KPI cards at the top:

| KPI | What It Shows |
|:---|:---|
| Total Slots | All non-maintenance slots in the system |
| Occupied | Currently active sessions |
| Available | Slots ready for allocation |
| Utilization % | Occupied ÷ (Total − Maintenance) × 100 |
| Today's Revenue | Sum of fees for sessions completed today |
| Vehicles Today | Unique vehicles that entered today |

Below the KPIs:
- **Zone Occupancy Chart** — pie chart by zone (A, B, C, etc.)
- **Revenue by Day** — last 14 days' bar chart
- **Recent Activity** — last 10 entry/exit events with timestamp

---

### 4.4 Search & Filter Records

Dual tabs: **Vehicle Search** and **Session Search**.

**Vehicle Search filters:**
- Plate number (partial match)
- Owner name (partial match)
- Vehicle type (All / Car / Bike / EV)

**Session Search filters:**
- Plate number
- Session status (All / Active / Completed)
- Slot code
- Date range (From → To)

Click **Clear Filters** to reset all fields instantly. Result count is shown above the table.

---

### 4.5 Monthly Calendar View

- Use **◀ / ▶** arrows to navigate between months.
- Each day cell shows: number of entries + total revenue.
- Cells are **heat-coloured**: deeper green = higher revenue.
- Click any date to see a **Day Detail Table** with every session that day.

---

## 5. TQM Quality Control Tools

### 5.1 Defect Checksheet

Use this page to **log quality observations** as you use the system or conduct test runs.

**Fields:**
| Field | Description |
|:---|:---|
| Date Found | Auto-set to today; editable |
| Module | Which part of the system the defect was found in |
| Description | Clear, factual description of the defect |
| Fishbone Category | People / Process / Software Code / Infrastructure |
| Defect Type | Short tag (used by Pareto chart) |
| Severity (1–10) | 1 = minor cosmetic, 10 = system down |
| Status | Open / In Progress / Resolved |

> **Demo rows** (marked `is_demo = 1`) are pre-seeded. Replace or delete them with your own real observations before submission.

---

### 5.2 FMEA Risk Audit

Displays the **Failure Mode and Effects Analysis** matrix.

**Tabs:**
- **Risk Matrix** — sortable table with all 12 failure modes. Out-of-control rows highlighted 🔴.
- **RPN Risk Chart** — horizontal bar chart sorted by RPN descending. Red line at RPN = 100 (action threshold).
- **Excel Export** — download the FMEA matrix as a formatted `.xlsx` workbook.

**Rating Scale:** Severity × Occurrence × Detection (each 1–10). See [`docs/FMEA.md`](FMEA.md) for the full rubric.

---

### 5.3 Pareto 80/20 Analysis

Automatically builds a **dual-axis bar + line chart** from live defect data:
- Bars: defect frequency by type (sorted descending)
- Line: cumulative percentage
- Dashed line: 80% reference cutoff

The **Vital Few** box identifies which defect types account for ≥80% of all quality problems.

> Chart is also saved to `docs/pareto_chart.png` and `exports/pareto_chart.png`.

---

### 5.4 Ishikawa Fishbone Diagram

Generates a **4-branch Ishikawa diagram** populated from defects currently in the checksheet database:

```
People ──────────┐
                 ├──→ Effect (Quality Failure)
Process ─────────┤
                 │
Software Code ───┤
                 │
Infrastructure ──┘
```

The **Effect label** at the head is editable. Click **Save Fishbone as PNG** to export.

---

### 5.5 PDCA Continuous Improvement

Tracks **Plan → Do → Check → Act** improvement cycles.

**Cycle Log tab:** Expand any cycle to see all four phases and a before/after metric comparison with a PDCA wheel diagram.

**Improvement Chart tab:** Bar chart comparing before/after metric values across all cycles.

**Log New Cycle tab:** Form to record a new improvement cycle in real-time.

---

### 5.6 SPC Control Chart

Plots **daily parking revenue** on an X-bar control chart:

| Element | Meaning |
|:---|:---|
| Yellow dashed line | X̄ — Process Mean |
| Red dashed line | UCL / LCL — Upper/Lower Control Limits (X̄ ± 3σ) |
| Green dots | In-control days |
| Red triangles | Out-of-control days — investigate for special causes |

Below the chart: a table of all days with their revenue and control status.

---

### 5.7 TQM Summary Report

One-click **6-sheet Excel export** for final submission:

| Sheet | Contents |
|:---|:---|
| CTQ Tree | 6 CTQ parameters with measurable targets |
| SIPOC | Full 8-row SIPOC matrix |
| Defect Checksheet | Complete defect log from the database |
| FMEA Matrix | All 12 failure modes ranked by RPN |
| PDCA Cycles | All logged improvement cycles |
| Control Chart Data | Daily revenue with UCL/LCL and control status |

Click **Generate Full TQM Report** → **Download TQM_Report.xlsx**.

---

## 6. Excel Reports & Export

From the **Excel Reports & Export** page (Q03 Usability Suite):

| Report | Contents |
|:---|:---|
| Session Report | All parking sessions with entry/exit times and fees |
| Daily Revenue Report | Aggregated revenue per day |
| Vehicle Registry | All registered vehicles with contact details |

Each report is formatted with styled headers and auto-sized columns.

---

## 7. Troubleshooting

| Problem | Solution |
|:---|:---|
| App won't start — `ModuleNotFoundError` | Run `pip install -r requirements.txt` inside the `.venv` |
| `parking.db` is corrupted | Delete `parking.db` and restart; schema and demo data re-seed automatically |
| Charts not rendering | Ensure `matplotlib` is installed; check console for `Agg` backend warnings |
| Dark mode not persisting | Check that `settings` table exists (`database/schema.sql` must have run via `init_db()`) |
| `git push` fails with port 443 timeout | Switch to mobile hotspot or VPN; campus firewall blocks GitHub HTTPS |
| Tests fail with FK error | Ensure `PRAGMA foreign_keys = ON` is in `get_connection()` — already present in `database/db.py` |

---

*Manual version 1.0 — generated for BBAT104 Review 3 / Final Submission.*
