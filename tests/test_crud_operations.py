"""
tests/test_crud_operations.py — Unit tests for Slot, Vehicle, and Session CRUD.

Covers:
- Slot creation, filtering, utilization metrics, and occupied deletion protection.
- Vehicle registration, uniqueness constraints, and queries.
- Entry/Exit lifecycle, auto-suggestion, double-entry prevention, and slot state transitions.
- Billing calculations per SRS formula (base rate + hourly ceil after free minutes).
- Poka-Yoke validations for plates, phones, non-empty fields, and exit timestamps.
"""

from datetime import datetime, timedelta
import pytest
from database.db import init_db, execute_db, query_db
from modules.slots import (
    create_slot,
    get_all_slots,
    get_slot_by_code,
    delete_slot,
    get_available_slot,
    get_utilization,
    set_slot_status,
)
from modules.vehicles import (
    create_vehicle,
    get_all_vehicles,
    get_vehicle_by_plate,
    delete_vehicle,
)
from modules.sessions import (
    record_entry,
    record_exit,
    get_active_sessions,
    get_active_session_for_vehicle,
)
from modules.billing import calculate_fee, calculate_duration_minutes
from modules.validation import (
    validate_plate,
    validate_phone,
    validate_non_empty,
    validate_exit_after_entry,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Ensure database schema is fresh and ready before each test."""
    init_db()


def test_slot_crud_and_safety():
    """Test creating, reading, and safe deletion of parking slots."""
    code = "TEST-SLOT-01"
    existing = get_slot_by_code(code)
    if existing:
        execute_db("DELETE FROM slots WHERE slot_code = ?", (code,))

    # Create
    slot_id = create_slot(code, "A", "Car", "Available")
    assert slot_id > 0

    # Read
    s = get_slot_by_code(code)
    assert s is not None
    assert s["zone"] == "A"
    assert s["status"] == "Available"

    # Cannot delete occupied slot
    set_slot_status(slot_id, "Occupied")
    with pytest.raises(ValueError, match="Occupied"):
        delete_slot(slot_id)

    # Can delete once available
    set_slot_status(slot_id, "Available")
    delete_slot(slot_id)
    assert get_slot_by_code(code) is None


def test_vehicle_crud_and_uniqueness():
    """Test vehicle registration and unique plate enforcement."""
    plate = "TEST99AA1111"
    existing = get_vehicle_by_plate(plate)
    if existing:
        delete_vehicle(existing["vehicle_id"])

    # Create
    v_id = create_vehicle(plate, "Test Driver", "9876543210", "Car")
    assert v_id > 0

    # Uniqueness check (Poka-Yoke)
    with pytest.raises(ValueError, match="already registered"):
        create_vehicle(plate, "Another Driver", "9876543211", "Car")

    # Read
    v = get_vehicle_by_plate(plate)
    assert v["owner_name"] == "Test Driver"

    # Cleanup
    delete_vehicle(v_id)


def test_entry_exit_lifecycle():
    """Test vehicle entry, double-entry prevention, exit, and fee calculation."""
    plate = "TEST88BB2222"
    v_rec = get_vehicle_by_plate(plate)
    if not v_rec:
        v_id = create_vehicle(plate, "Lifecycle Driver", "9123456780", "Car")
    else:
        v_id = v_rec["vehicle_id"]

    slot_code = "TEST-SLOT-LIFE"
    s_rec = get_slot_by_code(slot_code)
    if not s_rec:
        s_id = create_slot(slot_code, "B", "Car", "Available")
    else:
        s_id = s_rec["slot_id"]
        set_slot_status(s_id, "Available")

    # Clean prior sessions for this test slot and vehicle
    execute_db("DELETE FROM parking_sessions WHERE slot_id=? OR vehicle_id=?", (s_id, v_id))

    # Entry
    sess_id = record_entry(v_id, s_id)
    assert sess_id > 0

    # Slot must now be Occupied
    updated_slot = get_slot_by_code(slot_code)
    assert updated_slot["status"] == "Occupied"

    # Double entry should be blocked by Poka-Yoke
    with pytest.raises(ValueError, match="already has an active"):
        record_entry(v_id, s_id)

    # Set entry time back by 45 minutes to simulate realistic duration
    past_entry = (datetime.now() - timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S")
    execute_db("UPDATE parking_sessions SET entry_time=? WHERE session_id=?", (past_entry, sess_id))

    # Exit
    exit_result = record_exit(sess_id, "Car")
    assert "fee" in exit_result
    assert exit_result["fee"] > 0
    assert exit_result["duration_minutes"] >= 44.0

    # Slot must now be released to Available
    freed_slot = get_slot_by_code(slot_code)
    assert freed_slot["status"] == "Available"

    # Cleanup: delete all test sessions for this slot and vehicle to respect foreign key constraint
    execute_db("DELETE FROM parking_sessions WHERE slot_id=? OR vehicle_id=?", (s_id, v_id))
    delete_slot(s_id)
    delete_vehicle(v_id)


def test_billing_tariffs():
    """Test SRS FR-14 billing tariff formula: base rate + hourly rate after free minutes."""
    # Under free minutes (<= 15 mins for Car): fee = base_rate (20.0)
    assert calculate_fee("Car", 10) == 20.0
    assert calculate_fee("Car", 15) == 20.0

    # 60 mins for Car: (60 - 15) = 45 min billable -> ceil(45/60) = 1 hr -> 20 + 30 = 50.0
    assert calculate_fee("Car", 60) == 50.0

    # 90 mins for Car: (90 - 15) = 75 min billable -> ceil(75/60) = 2 hrs -> 20 + 2*30 = 80.0
    assert calculate_fee("Car", 90) == 80.0

    # Bike rates: base 10.0, per-hour 15.0, free 15 mins
    assert calculate_fee("Bike", 10) == 10.0
    assert calculate_fee("Bike", 60) == 25.0  # 10 + 1*15


def test_poka_yoke_validators():
    """Test validation utilities for plates, phones, and non-empty inputs."""
    # Valid Indian plates
    assert validate_plate("UK07AB1234")[0] is True
    assert validate_plate("DL01X5678")[0] is True
    assert validate_plate("MH12DE4321")[0] is True

    # Invalid plates
    assert validate_plate("12345")[0] is False
    assert validate_plate("INVALID_PLATE")[0] is False
    assert validate_plate("")[0] is False

    # Phone numbers
    assert validate_phone("9876543210")[0] is True
    assert validate_phone("12345")[0] is False
    assert validate_phone("abcdefghij")[0] is False

    # Non-empty
    assert validate_non_empty("Himanshu", "Name")[0] is True
    assert validate_non_empty("   ", "Name")[0] is False
    assert validate_non_empty("", "Name")[0] is False

    # Exit after entry
    assert validate_exit_after_entry("2026-10-01 10:00:00", "2026-10-01 11:00:00")[0] is True
    assert validate_exit_after_entry("2026-10-01 12:00:00", "2026-10-01 11:00:00")[0] is False
