"""
database/seed.py — Demo data loader for the Parking Management System.

PURPOSE: Populate the database with clearly labelled DEMO rows so the app
         has something to display during development and demos.

WARNING: Every row inserted here has is_demo = 1 (where applicable) and is
         labelled '[DEMO]' in text fields.  Replace or delete these rows
         before submitting as real quality observations.

Run:  python database/seed.py
      (idempotent — skips rows that already exist)
"""

import sys
import os

# Allow running from the project root or from this directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.db import init_db, execute_db, query_db
from config import DEFAULT_TARIFF, PARKING_ZONES


def seed_slots() -> None:
    """Insert demo parking slots across four zones if they don't already exist."""
    slot_definitions = [
        # (slot_code, zone, slot_type)
        ("A-C-01", "A", "Car"), ("A-C-02", "A", "Car"), ("A-C-03", "A", "Car"),
        ("A-B-01", "A", "Bike"), ("A-B-02", "A", "Bike"),
        ("B-C-01", "B", "Car"), ("B-C-02", "B", "Car"),
        ("B-EV-01", "B", "EV"), ("B-EV-02", "B", "EV"),
        ("C-C-01", "C", "Car"), ("C-C-02", "C", "Car"),
        ("C-B-01", "C", "Bike"),
        ("D-C-01", "D", "Car"),
        ("D-DIS-01", "D", "Disabled"), ("D-DIS-02", "D", "Disabled"),
    ]
    existing = {r["slot_code"] for r in query_db("SELECT slot_code FROM slots")}
    for code, zone, stype in slot_definitions:
        if code not in existing:
            execute_db(
                "INSERT INTO slots (slot_code, zone, slot_type) VALUES (?,?,?)",
                (code, zone, stype),
            )
    print(f"  slots: {len(slot_definitions)} definitions checked.")


def seed_tariff() -> None:
    """Insert default tariff rates if the table is empty."""
    if query_db("SELECT 1 FROM tariff LIMIT 1"):
        print("  tariff: already seeded, skipping.")
        return
    for vtype, (base, per_hour, free_min) in DEFAULT_TARIFF.items():
        execute_db(
            "INSERT INTO tariff (vehicle_type, base_rate, per_hour_rate, free_minutes) VALUES (?,?,?,?)",
            (vtype, base, per_hour, free_min),
        )
    print(f"  tariff: {len(DEFAULT_TARIFF)} rows inserted.")


def seed_vehicles() -> None:
    """Insert a small set of DEMO vehicles if they don't exist yet."""
    demo_vehicles = [
        # (plate_no, owner_name, phone, vehicle_type)
        ("UK07AB1234", "[DEMO] Rajesh Kumar",   "9876543210", "Car"),
        ("UK07CD5678", "[DEMO] Priya Sharma",   "9123456789", "Bike"),
        ("HR26EV9012", "[DEMO] Ankit Singh",    "9988776655", "EV"),
        ("DL01XY3456", "[DEMO] Meena Verma",    "9001122334", "Car"),
        ("UP32GH7890", "[DEMO] Suresh Patel",   "9765432109", "Bike"),
    ]
    existing = {r["plate_no"] for r in query_db("SELECT plate_no FROM vehicles")}
    inserted = 0
    for plate, owner, phone, vtype in demo_vehicles:
        if plate not in existing:
            execute_db(
                "INSERT INTO vehicles (plate_no, owner_name, phone, vehicle_type) VALUES (?,?,?,?)",
                (plate, owner, phone, vtype),
            )
            inserted += 1
    print(f"  vehicles: {inserted} DEMO vehicles inserted.")


def seed_settings() -> None:
    """Insert default theme settings if not already present."""
    defaults = [
        ("dark_mode", "true"),
        ("palette",   "Ocean"),
    ]
    existing = {r["key"] for r in query_db("SELECT key FROM settings")}
    for key, value in defaults:
        if key not in existing:
            execute_db("INSERT INTO settings (key, value) VALUES (?,?)", (key, value))
    print("  settings: defaults ensured.")


def seed_defects() -> None:
    """Insert DEMO defect rows so the Pareto/Fishbone charts have data to show.

    All rows have is_demo = 1 and must be replaced with real observations.
    """
    demo_defects = [
        # (module, description, fishbone_category, defect_type, severity, status)
        ("Entry",    "[DEMO] Slot suggestion showed wrong type",   "Software Code",    "Logic Error",      6, "Resolved"),
        ("Billing",  "[DEMO] Fee rounded incorrectly for EV",      "Software Code",    "Calculation Bug",  7, "Resolved"),
        ("Vehicles", "[DEMO] Duplicate plate allowed briefly",     "Process",          "Validation Gap",   8, "Resolved"),
        ("Exit",     "[DEMO] Exit time accepted before entry",     "Software Code",    "Validation Gap",   9, "Resolved"),
        ("Reports",  "[DEMO] Excel column width too narrow",       "Infrastructure",   "UI Issue",         3, "Resolved"),
        ("DB",       "[DEMO] FK not enforced in early schema",     "Infrastructure",   "Config Error",     5, "Resolved"),
    ]
    if query_db("SELECT 1 FROM defects WHERE is_demo=1 LIMIT 1"):
        print("  defects: DEMO rows already present, skipping.")
        return
    for mod, desc, fb_cat, dtype, sev, status in demo_defects:
        execute_db(
            """INSERT INTO defects
               (module, description, fishbone_category, defect_type, severity, status, is_demo)
               VALUES (?,?,?,?,?,?,1)""",
            (mod, desc, fb_cat, dtype, sev, status),
        )
    print(f"  defects: {len(demo_defects)} DEMO rows inserted.")


if __name__ == "__main__":
    print("Initialising database …")
    init_db()
    print("Seeding DEMO data …")
    seed_tariff()
    seed_slots()
    seed_vehicles()
    seed_settings()
    seed_defects()
    print("\nDone.  All DEMO rows are marked is_demo=1.")
    print("Replace them with real observations before final submission.")
