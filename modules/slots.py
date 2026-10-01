"""
modules/slots.py — Parking slot CRUD operations.

Business rule enforced here (not just in the UI):
- A slot that is 'Occupied' cannot be deleted (active session depends on it).

Why here and not only in the DB: SQLite FK constraints don't prevent deleting
a slot while a session references it unless ON DELETE RESTRICT is set.  We
enforce it explicitly so the error message is user-friendly.
"""

from database.db import query_db, execute_db


# ─── Read ────────────────────────────────────────────────────────────────────

def get_all_slots(zone: str = None, slot_type: str = None,
                  status: str = None) -> list[dict]:
    """Return all slots, optionally filtered by zone, type, or status."""
    sql = "SELECT * FROM slots WHERE 1=1"
    params: list = []
    if zone:
        sql += " AND zone = ?"
        params.append(zone)
    if slot_type:
        sql += " AND slot_type = ?"
        params.append(slot_type)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY zone, slot_code"
    return query_db(sql, tuple(params))


def get_slot_by_id(slot_id: int) -> dict | None:
    """Return a single slot row by primary key, or None if not found."""
    rows = query_db("SELECT * FROM slots WHERE slot_id = ?", (slot_id,))
    return rows[0] if rows else None


def get_slot_by_code(slot_code: str) -> dict | None:
    """Return a slot row by its unique slot_code, or None."""
    rows = query_db("SELECT * FROM slots WHERE slot_code = ?", (slot_code,))
    return rows[0] if rows else None


def get_available_slot(vehicle_type: str) -> dict | None:
    """Return the first Available slot matching the vehicle type.

    Slot type 'Disabled' is mapped to vehicle type 'Car' for allocation.
    This supports the CTQ: auto-suggest on entry to minimize queue time.
    """
    # EV vehicles go to EV slots; Bikes to Bike slots; Cars to Car or Disabled slots.
    if vehicle_type == "EV":
        type_filter = ("EV",)
        placeholders = "(?)"
    elif vehicle_type == "Bike":
        type_filter = ("Bike",)
        placeholders = "(?)"
    else:  # Car (and fallback)
        type_filter = ("Car", "Disabled")
        placeholders = "(?,?)"

    sql = (
        f"SELECT * FROM slots WHERE status = 'Available' "
        f"AND slot_type IN {placeholders} "
        f"ORDER BY zone, slot_code LIMIT 1"
    )
    rows = query_db(sql, type_filter)
    return rows[0] if rows else None


def get_utilization() -> dict:
    """Return occupancy stats: occupied, available, maintenance, total, utilization_pct."""
    rows = query_db(
        "SELECT status, COUNT(*) AS cnt FROM slots GROUP BY status"
    )
    counts = {r["status"]: r["cnt"] for r in rows}
    occupied    = counts.get("Occupied", 0)
    available   = counts.get("Available", 0)
    maintenance = counts.get("Maintenance", 0)
    total       = occupied + available + maintenance
    non_maint   = occupied + available
    util_pct    = round((occupied / non_maint * 100), 1) if non_maint else 0.0
    return {
        "occupied": occupied,
        "available": available,
        "maintenance": maintenance,
        "total": total,
        "utilization_pct": util_pct,
    }


# ─── Create ──────────────────────────────────────────────────────────────────

def create_slot(slot_code: str, zone: str, slot_type: str,
                status: str = "Available") -> int:
    """Insert a new slot row.  Returns the new slot_id."""
    return execute_db(
        "INSERT INTO slots (slot_code, zone, slot_type, status) VALUES (?,?,?,?)",
        (slot_code.strip().upper(), zone, slot_type, status),
    )


# ─── Update ──────────────────────────────────────────────────────────────────

def update_slot(slot_id: int, zone: str, slot_type: str, status: str) -> None:
    """Update zone, type, and status for an existing slot."""
    execute_db(
        "UPDATE slots SET zone=?, slot_type=?, status=? WHERE slot_id=?",
        (zone, slot_type, status, slot_id),
    )


def set_slot_status(slot_id: int, status: str) -> None:
    """Set just the status field (used by entry/exit logic)."""
    execute_db(
        "UPDATE slots SET status=? WHERE slot_id=?",
        (status, slot_id),
    )


# ─── Delete ──────────────────────────────────────────────────────────────────

def delete_slot(slot_id: int) -> None:
    """Delete a slot.  Raises ValueError if the slot is currently Occupied."""
    slot = get_slot_by_id(slot_id)
    if slot is None:
        raise ValueError(f"Slot ID {slot_id} not found.")
    if slot["status"] == "Occupied":
        raise ValueError(
            f"Cannot delete slot '{slot['slot_code']}' — it is currently Occupied. "
            "Complete the active session first."
        )
    execute_db("DELETE FROM slots WHERE slot_id=?", (slot_id,))
