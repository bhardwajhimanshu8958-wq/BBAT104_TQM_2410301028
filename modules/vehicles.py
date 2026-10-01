"""
modules/vehicles.py — Vehicle registration CRUD.

Plate number uniqueness is enforced at both the DB level (UNIQUE constraint)
and here (friendly error before the DB raises an IntegrityError).
"""

import sqlite3
from database.db import query_db, execute_db


# ─── Read ────────────────────────────────────────────────────────────────────

def get_all_vehicles(vehicle_type: str = None, search: str = None) -> list[dict]:
    """Return all vehicles, with optional type filter and text search.

    Args:
        vehicle_type: Filter by 'Car', 'Bike', or 'EV'. None = all.
        search:       Case-insensitive substring match on plate_no or owner_name.
    """
    sql = "SELECT * FROM vehicles WHERE 1=1"
    params: list = []
    if vehicle_type:
        sql += " AND vehicle_type = ?"
        params.append(vehicle_type)
    if search:
        sql += " AND (plate_no LIKE ? OR owner_name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    sql += " ORDER BY created_at DESC"
    return query_db(sql, tuple(params))


def get_vehicle_by_id(vehicle_id: int) -> dict | None:
    """Return a single vehicle by primary key, or None."""
    rows = query_db("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
    return rows[0] if rows else None


def get_vehicle_by_plate(plate_no: str) -> dict | None:
    """Return a vehicle row by plate number (case-insensitive), or None."""
    rows = query_db(
        "SELECT * FROM vehicles WHERE UPPER(plate_no) = UPPER(?)",
        (plate_no.strip(),),
    )
    return rows[0] if rows else None


# ─── Create ──────────────────────────────────────────────────────────────────

def create_vehicle(plate_no: str, owner_name: str,
                   phone: str, vehicle_type: str) -> int:
    """Register a new vehicle.  Returns the new vehicle_id.

    Raises:
        ValueError: If the plate number is already registered.
    """
    plate_no = plate_no.strip().upper()
    if get_vehicle_by_plate(plate_no):
        raise ValueError(
            f"Plate number '{plate_no}' is already registered.  "
            "Use a different plate or update the existing record."
        )
    try:
        return execute_db(
            "INSERT INTO vehicles (plate_no, owner_name, phone, vehicle_type) VALUES (?,?,?,?)",
            (plate_no, owner_name.strip(), phone.strip(), vehicle_type),
        )
    except sqlite3.IntegrityError as exc:
        # Second safety net in case of a race condition
        raise ValueError(f"Database integrity error: {exc}") from exc


# ─── Update ──────────────────────────────────────────────────────────────────

def update_vehicle(vehicle_id: int, owner_name: str,
                   phone: str, vehicle_type: str) -> None:
    """Update owner name, phone, and vehicle type.  Plate is immutable after registration."""
    execute_db(
        "UPDATE vehicles SET owner_name=?, phone=?, vehicle_type=? WHERE vehicle_id=?",
        (owner_name.strip(), phone.strip(), vehicle_type, vehicle_id),
    )


# ─── Delete ──────────────────────────────────────────────────────────────────

def delete_vehicle(vehicle_id: int) -> None:
    """Delete a vehicle record.

    Raises:
        ValueError: If the vehicle has an active parking session.
    """
    active = query_db(
        "SELECT 1 FROM parking_sessions WHERE vehicle_id=? AND status='Active'",
        (vehicle_id,),
    )
    if active:
        raise ValueError(
            "Cannot delete this vehicle — it currently has an active parking session. "
            "Complete the exit first."
        )
    execute_db("DELETE FROM vehicles WHERE vehicle_id=?", (vehicle_id,))


# ─── Stats ───────────────────────────────────────────────────────────────────

def count_vehicles_today() -> int:
    """Return the number of distinct vehicles that entered today (for the dashboard)."""
    rows = query_db(
        """SELECT COUNT(DISTINCT vehicle_id) AS cnt
           FROM parking_sessions
           WHERE date(entry_time) = date('now','localtime')"""
    )
    return rows[0]["cnt"] if rows else 0
