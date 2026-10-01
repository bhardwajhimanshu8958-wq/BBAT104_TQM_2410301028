-- schema.sql — Parking Management System database schema
-- Run via database/db.py::init_db() or directly:  sqlite3 parking.db < schema.sql
-- All domain columns have CHECK constraints so the DB enforces integrity even outside the UI.

PRAGMA foreign_keys = ON;

-- ─── Parking slots ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS slots (
    slot_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    slot_code TEXT    UNIQUE NOT NULL,
    zone      TEXT    NOT NULL,
    slot_type TEXT    NOT NULL CHECK(slot_type IN ('Car','Bike','EV','Disabled')),
    status    TEXT    NOT NULL DEFAULT 'Available'
                     CHECK(status IN ('Available','Occupied','Maintenance'))
);

-- ─── Registered vehicles ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_no     TEXT    UNIQUE NOT NULL,
    owner_name   TEXT    NOT NULL,
    phone        TEXT,
    vehicle_type TEXT    NOT NULL CHECK(vehicle_type IN ('Car','Bike','EV')),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ─── Tariff rates per vehicle type ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tariff (
    vehicle_type  TEXT PRIMARY KEY CHECK(vehicle_type IN ('Car','Bike','EV')),
    base_rate     REAL NOT NULL CHECK(base_rate >= 0),
    per_hour_rate REAL NOT NULL CHECK(per_hour_rate >= 0),
    free_minutes  INTEGER NOT NULL DEFAULT 0 CHECK(free_minutes >= 0)
);

-- ─── Parking sessions ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS parking_sessions (
    session_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_id  INTEGER NOT NULL REFERENCES vehicles(vehicle_id),
    slot_id     INTEGER NOT NULL REFERENCES slots(slot_id),
    entry_time  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    exit_time   TEXT,
    fee         REAL,
    status      TEXT    NOT NULL DEFAULT 'Active'
                        CHECK(status IN ('Active','Completed'))
);

-- ─── App settings (theme, dark mode) ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- ─── Defect checksheet ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS defects (
    defect_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    date_found         TEXT    NOT NULL DEFAULT (date('now','localtime')),
    module             TEXT    NOT NULL,
    description        TEXT    NOT NULL,
    fishbone_category  TEXT    NOT NULL
                       CHECK(fishbone_category IN ('People','Process','Software Code','Infrastructure')),
    defect_type        TEXT    NOT NULL,
    severity           INTEGER NOT NULL CHECK(severity BETWEEN 1 AND 10),
    status             TEXT    NOT NULL DEFAULT 'Open'
                       CHECK(status IN ('Open','In Progress','Resolved')),
    resolution         TEXT,
    is_demo            INTEGER NOT NULL DEFAULT 0 CHECK(is_demo IN (0,1))
);

-- ─── FMEA matrix ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fmea (
    fmea_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    process_step  TEXT    NOT NULL,
    failure_mode  TEXT    NOT NULL,
    effect        TEXT    NOT NULL,
    cause         TEXT    NOT NULL,
    severity      INTEGER NOT NULL CHECK(severity BETWEEN 1 AND 10),
    occurrence    INTEGER NOT NULL CHECK(occurrence BETWEEN 1 AND 10),
    detection     INTEGER NOT NULL CHECK(detection BETWEEN 1 AND 10),
    rpn           INTEGER NOT NULL,   -- computed in code: severity * occurrence * detection
    mitigation    TEXT,
    status        TEXT    NOT NULL DEFAULT 'Open' CHECK(status IN ('Open','Mitigated'))
);

-- RPN view for quick sorting
CREATE VIEW IF NOT EXISTS fmea_rpn AS
    SELECT *, severity * occurrence * detection AS computed_rpn
    FROM fmea
    ORDER BY computed_rpn DESC;

-- ─── PDCA cycle log ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pdca (
    pdca_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_no     INTEGER NOT NULL,
    plan         TEXT    NOT NULL,
    do_action    TEXT    NOT NULL,
    check_result TEXT    NOT NULL,
    act_decision TEXT    NOT NULL,
    metric_name  TEXT    NOT NULL,
    before_value REAL    NOT NULL,
    after_value  REAL    NOT NULL,
    date         TEXT    NOT NULL DEFAULT (date('now','localtime'))
);
