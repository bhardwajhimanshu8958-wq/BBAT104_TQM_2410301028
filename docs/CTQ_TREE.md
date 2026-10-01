# CTQ Tree — Parking Management System

**Course:** BBAT104 TQM | **Quality Goal:** Q03 — Improve Usability  
**Student:** Himanshu Bhardwaj | Roll No. 2410301028

---

## What is a CTQ Tree?

A **Critical-to-Quality (CTQ) Tree** translates broad customer needs into specific, measurable quality characteristics. The structure is:

```
Customer NEED
  └── Quality DRIVER (the dimension of quality that satisfies the need)
        └── CTQ (measurable, testable specification)
```

**Why this tool?** CTQ trees prevent vague quality goals (e.g. "make it fast") from slipping through to delivery without a testable target. They force every need to have a number attached.

---

## CTQ Tree

### Need 1: Fast Vehicle Entry

| Driver | CTQ | Target / Threshold |
|--------|-----|--------------------|
| Minimal queue time | Entry processing time (slot suggestion + session creation) | ≤ 30 seconds per vehicle |
| No double entry | Duplicate active-session check | 0 vehicles double-entered (100% blocked by Poka-Yoke) |
| Correct slot allocation | Slot type match rate | 100% — only slots matching vehicle type are suggested |
| Correct slot suggested | Auto-suggest correctness | First Available matching slot always proposed (no manual search) |

---

### Need 2: Maximum Space Utilization

| Driver | CTQ | Target / Threshold |
|--------|-----|--------------------|
| High occupancy | Real-time utilization metric | ≥ 80% occupancy during peak hours (displayable on dashboard) |
| Accurate slot status | Slot status accuracy | 0 slots with incorrect status (Available/Occupied/Maintenance must be DB-consistent) |
| Maintenance tracking | % slots in Maintenance vs total | Displayed on dashboard; maintenance slots excluded from utilization denominator |

---

### Need 3: Correct Billing

| Driver | CTQ | Target / Threshold |
|--------|-----|--------------------|
| Accurate fee calculation | Fee error rate | 0 incorrect fee calculations (unit-tested for all vehicle types and edge cases) |
| Transparent tariff | Tariff legibility | Tariff table visible to operator; no hardcoded rates |
| Free-minute grace | Free-minute enforcement | Fee = base rate when duration ≤ free_minutes; validated by unit tests |

---

### Need 4: Usable Interface (Q03)

| Driver | CTQ | Target / Threshold |
|--------|-----|--------------------|
| Eye comfort | Dark Mode availability | Toggle present in sidebar; applies in ≤ 1 second; persists across sessions |
| Visual personalization | Custom Themes | ≥ 5 palettes; swatch visible before selection |
| Situational awareness | Dashboard KPIs | 6 KPI cards + 2 charts load in ≤ 3 seconds with 1,000 sessions |
| Fast record lookup | Search Filters | Plate/owner/date-range filter returns results in ≤ 2 seconds on 1,000 records |
| Historical overview | Calendar View | Month view renders in ≤ 3 seconds; daily revenue heat-coloured; day-detail on click |

---

### Need 5: Data Integrity and No Crashes

| Driver | CTQ | Target / Threshold |
|--------|-----|--------------------|
| Valid inputs only | Poka-Yoke error rate | 0 raw tracebacks shown to user; all invalid inputs caught with friendly message |
| Plate format | Regex match rate | 100% of plates validated against Indian plate format before save |
| Phone format | Digit count check | 100% of phones checked for exactly 10 digits |
| No invalid exit | Exit-before-entry prevention | System blocks exit timestamp < entry timestamp; 0 such records created |
| DB constraint coverage | DB CHECK/UNIQUE coverage | All domain columns have CHECK constraints; enforced at DB level, not just UI |

---

### Need 6: TQM Evidence and Auditability

| Driver | CTQ | Target / Threshold |
|--------|-----|--------------------|
| Defect traceability | Error Log completeness | Every real defect found in development has an entry in `docs/ERROR_LOG.md` |
| Risk management | FMEA coverage | ≥ 12 failure modes documented; all with S, O, D ratings and RPN |
| Quality improvement | PDCA cycles | ≥ 2 complete cycles with before/after metric values |
| Commit hygiene | Git commit count | ≥ 25 commits; linear history; no force-pushes |
| Test coverage | pytest pass rate | 100% of unit tests pass at `git push`; no skips |

---

## CTQ Summary Table

| # | Need | Driver | CTQ | Target |
|---|------|--------|-----|--------|
| 1 | Fast entry | Queue time | Entry processing time | ≤ 30 s |
| 2 | Fast entry | No duplicates | Double-entry rate | 0 |
| 3 | Space utilization | Occupancy | Real-time utilization % | ≥ 80% |
| 4 | Space utilization | Accuracy | Slot status accuracy | 0 errors |
| 5 | Correct billing | Fee accuracy | Fee error rate | 0 |
| 6 | Usability | Comfort | Dark mode response | ≤ 1 s |
| 7 | Usability | Personalization | Theme count | ≥ 5 |
| 8 | Usability | Awareness | Dashboard load time | ≤ 3 s |
| 9 | Usability | Lookup | Filter response time | ≤ 2 s |
| 10 | Data integrity | Input validation | Traceback rate | 0 |
| 11 | TQM evidence | Risk coverage | FMEA failure modes | ≥ 12 |
| 12 | TQM evidence | Improvement | PDCA cycles | ≥ 2 |
