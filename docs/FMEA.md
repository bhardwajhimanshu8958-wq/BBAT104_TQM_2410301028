# FMEA Risk Assessment Matrix — Smart Parking Management System

**Course:** BBAT104 Fundamentals of Total Quality Management (TQM)  
**Student:** Himanshu Bhardwaj | Roll No: 2410301028 | Section: B.Tech CSE Sec A  
**Baseline System:** Parking Management System  
**Review Phase:** Phase 4 — Risk Audit

---

## 1. Why FMEA Was Applied

**Failure Mode and Effects Analysis (FMEA)** is a systematic proactive risk assessment technique used in TQM to:
- **Identify potential failure modes** before they reach production.
- **Quantify risk** using the Risk Priority Number (RPN) formula.
- **Prioritize corrective actions** on the highest-impact failure modes.

It was selected for this system because entry queuing and billing accuracy are directly tied to software correctness — FMEA provides a traceable audit trail that every critical path is guarded.

---

## 2. Rating Rubric (Standardised Scale)

| Rating | Severity (S) | Occurrence (O) | Detection (D) |
| :---: | :--- | :--- | :--- |
| **1** | No impact — cosmetic only | Remote probability (1 in 10,000+) | Will be caught immediately by automated test |
| **3** | Minor inconvenience | Low probability (1 in 1,000) | Very likely to be caught before release |
| **5** | Moderate degradation | Occasional (1 in 100) | May be caught after some debugging |
| **7** | System feature unusable | Frequent (1 in 20) | Unlikely to be caught before deployment |
| **10** | Full system shutdown / data loss | Near certainty (1 in 3 or higher) | Will not be caught without dedicated monitoring |

**Action Threshold**: RPN > 100 requires immediate corrective action before release.  
**RPN Formula**: **RPN = S × O × D**

---

## 3. FMEA Risk Matrix (12 Failure Modes)

| ID | Process Step | Failure Mode | Potential Effect | Root Cause | S | O | D | **RPN** | Mitigation Strategy | After-Mitigation RPN | Status |
|:--:|:---|:---|:---|:---|:--:|:--:|:--:|:--:|:---|:--:|:---|
| 1 | Vehicle Entry | Duplicate active session created | Two sessions for same vehicle; data corruption | No session check before record_entry() | 9 | 3 | 2 | **54** | Added session pre-check in record_entry(); raises ValueError | 9 | ✅ Resolved |
| 2 | Vehicle Entry | Invalid plate format accepted | Corrupt vehicle record; mis-billing | Regex validator not applied | 8 | 4 | 3 | **96** | validate_plate() Poka-Yoke applied before DB insert | 8 | ✅ Resolved |
| 3 | Vehicle Exit | Exit time before entry accepted | Negative duration; invalid receipt | No timestamp comparison guard | 8 | 2 | 3 | **48** | validate_exit_after_entry() Poka-Yoke guard | 8 | ✅ Resolved |
| 4 | Vehicle Exit | Fee calculated as zero or negative | Revenue loss; wrong audit trail | Duration ≤ 0 due to same-second exit | 9 | 2 | 2 | **36** | raise ValueError in calculate_duration_minutes if delta ≤ 0 | 9 | ✅ Resolved |
| 5 | Slot Allocation | Wrong slot type assigned (EV → Car) | EV vehicle has no charger; CTQ failure | Type filter bug in get_available_slot() | 7 | 3 | 4 | **84** | Unit tested type filter; separate tuple filters for Bike/EV/Car | 7 | ✅ Resolved |
| 6 | Slot Management | Occupied slot deleted | Session references deleted slot; FK error | No occupancy check before DELETE | 8 | 3 | 2 | **48** | delete_slot() raises ValueError if status = 'Occupied' | 8 | ✅ Resolved |
| 7 | Database | FK constraint not enforced on delete | Orphaned sessions; slot stuck Occupied | SQLite FK off by default | 8 | 3 | 3 | **72** | PRAGMA foreign_keys=ON in get_connection() | 8 | ✅ Resolved |
| 8 | Billing | Free minutes not deducted correctly | Overcharge; customer complaint | Off-by-one in free_minutes comparison | 6 | 4 | 5 | **120** 🔴 | Explicit unit test: calculate_fee('Car',10)==20.0 verified | 18 | ✅ Resolved |
| 9 | UI / Streamlit | Page crashes on empty DB state | App unusable on fresh install | Missing None check on query results | 7 | 5 | 4 | **140** 🔴 | All query results guarded with 'if rows else default' | 21 | ✅ Resolved |
| 10 | Reports | Excel column width too narrow | Data truncated; unreadable export | _auto_size_columns() not called first | 3 | 5 | 6 | **90** | Auto-sizer called for every sheet in export functions | 9 | ✅ Resolved |
| 11 | Network / Push | git push fails mid-session | Commits lost; GitHub desync | Unstable Wi-Fi / firewall block on :443 | 9 | 4 | 2 | **72** | Documented in ERROR_LOG.md; mobile hotspot fallback protocol | 18 | ✅ Resolved |
| 12 | Vehicle Registry | Phone stored as non-normalized text | Search by phone fails; Poka-Yoke gap | No phone normalization in create_vehicle | 4 | 6 | 5 | **120** 🔴 | validate_phone() normalizes and validates before insert | 12 | ✅ Resolved |

---

## 4. Top 5 Risk Areas (Pre-Mitigation RPN)

| Rank | Process Area | Failure Mode | Pre-Mit. RPN | Post-Mit. RPN | Reduction |
|:---:|:---|:---|:---:|:---:|:---:|
| 🥇 1 | UI / Streamlit | Page crashes on empty DB | **140** 🔴 | 21 | ↓ 85% |
| 🥈 2 | Billing | Free minutes not deducted | **120** 🔴 | 18 | ↓ 85% |
| 🥉 3 | Vehicle Registry | Phone format issue | **120** 🔴 | 12 | ↓ 90% |
| 4 | Vehicle Entry | Invalid plate accepted | 96 | 8 | ↓ 92% |
| 5 | Slot Allocation | Wrong type assigned | 84 | 7 | ↓ 92% |

---

## 5. Corrective Action Summary

All 12 failure modes have been addressed through code implementation, Poka-Yoke validation, and automated testing. No open critical risks (RPN > 100) remain post-mitigation. PDCA Cycle 1 addresses the top billing defect (ID #8) as its improvement subject.
