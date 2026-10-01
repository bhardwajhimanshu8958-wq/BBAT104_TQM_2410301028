"""
modules/sessions.py — Vehicle entry, exit, and session query operations.

Key business rules enforced here:
- A vehicle cannot enter if it already has an Active session (Poka-Yoke).
- A slot is marked Occupied on entry and Available on exit.
- Fee is calculated at exit time using modules/billing.py.
- Exit time is stored as the current local datetime; no backdating allowed.
"""

from datetime import datetime
from database.db import query_db, execute_db
from modules.billing import calculate_duration_minutes, calculate_fee
from modules.slots import set_slot_status

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ─── Entry ───────────────────────────────────────────────────────────────────

def record_entry(vehicle_id: int, slot_id: int) -> int:
    """Create a new Active parking session and mark the slot Occupied.

    Args:
        vehicle_id: FK to vehicles table.
        slot_id:    FK to slots table (must be Available).

    Returns:
        The new session_id.

    Raises:
        ValueError: If the vehicle already has an Active session.
    """
    # Poka-Yoke: prevent double entry
    active = query_db(
        "SELECT session_id FROM parking_sessions WHERE vehicle_id=? AND status='Active'",
        (vehicle_id,),
    )
    if active:
        raise ValueError(
            "This vehicle already has an active parking session "
            f"(session #{active[0]['session_id']}).  "
            "Complete the exit before registering a new entry."
        )

    entry_time = datetime.now().strftime(TIME_FORMAT)
    session_id = execute_db(
        """INSERT INTO parking_sessions (vehicle_id, slot_id, entry_time, status)
           VALUES (?,?,?,'Active')""",
        (vehicle_id, slot_id, entry_time),
    )
    set_slot_status(slot_id, "Occupied")
    return session_id


# ─── Exit ────────────────────────────────────────────────────────────────────

def record_exit(session_id: int, vehicle_type: str) -> dict:
    """Close an Active session, compute fee, free the slot.

    Args:
        session_id:   The active session to close.
        vehicle_type: Used to look up the tariff (from the vehicle record).

    Returns:
        A dict with {fee, duration_minutes, exit_time}.

    Raises:
        ValueError: If the session is not found or already Completed.
    """
    rows = query_db(
        "SELECT * FROM parking_sessions WHERE session_id=?",
        (session_id,),
    )
    if not rows:
        raise ValueError(f"Session #{session_id} not found.")
    session = rows[0]
    if session["status"] != "Active":
        raise ValueError(
            f"Session #{session_id} is already '{session['status']}'; cannot exit again."
        )

    exit_time        = datetime.now().strftime(TIME_FORMAT)
    duration_minutes = calculate_duration_minutes(session["entry_time"], exit_time)
    fee              = calculate_fee(vehicle_type, duration_minutes)

    execute_db(
        """UPDATE parking_sessions
           SET exit_time=?, fee=?, status='Completed'
           WHERE session_id=?""",
        (exit_time, fee, session_id),
    )
    set_slot_status(session["slot_id"], "Available")

    return {
        "fee":              fee,
        "duration_minutes": round(duration_minutes, 1),
        "exit_time":        exit_time,
    }


# ─── Queries ─────────────────────────────────────────────────────────────────

def get_active_session_for_vehicle(vehicle_id: int) -> dict | None:
    """Return the Active session for a vehicle, or None if not parked."""
    rows = query_db(
        """SELECT ps.*, s.slot_code, v.plate_no, v.vehicle_type
           FROM parking_sessions ps
           JOIN slots    s ON ps.slot_id    = s.slot_id
           JOIN vehicles v ON ps.vehicle_id = v.vehicle_id
           WHERE ps.vehicle_id=? AND ps.status='Active'""",
        (vehicle_id,),
    )
    return rows[0] if rows else None


def get_all_sessions(status: str = None, plate: str = None,
                     owner: str = None, slot_code: str = None,
                     from_date: str = None, to_date: str = None) -> list[dict]:
    """Return sessions with rich vehicle and slot info, with optional filters."""
    sql = """
        SELECT ps.session_id, ps.entry_time, ps.exit_time, ps.fee, ps.status,
               v.plate_no, v.owner_name, v.vehicle_type,
               s.slot_code, s.zone
        FROM parking_sessions ps
        JOIN vehicles v ON ps.vehicle_id = v.vehicle_id
        JOIN slots    s ON ps.slot_id    = s.slot_id
        WHERE 1=1
    """
    params: list = []
    if status:
        sql += " AND ps.status = ?"
        params.append(status)
    if plate:
        sql += " AND v.plate_no LIKE ?"
        params.append(f"%{plate}%")
    if owner:
        sql += " AND v.owner_name LIKE ?"
        params.append(f"%{owner}%")
    if slot_code:
        sql += " AND s.slot_code LIKE ?"
        params.append(f"%{slot_code}%")
    if from_date:
        sql += " AND date(ps.entry_time) >= ?"
        params.append(from_date)
    if to_date:
        sql += " AND date(ps.entry_time) <= ?"
        params.append(to_date)
    sql += " ORDER BY ps.entry_time DESC"
    return query_db(sql, tuple(params))


def get_active_sessions() -> list[dict]:
    """Return all currently Active sessions with vehicle and slot details."""
    return get_all_sessions(status="Active")


def get_recent_activity(limit: int = 10) -> list[dict]:
    """Return the most recent N sessions (for the dashboard activity table)."""
    sql = """
        SELECT ps.session_id, ps.entry_time, ps.exit_time, ps.fee, ps.status,
               v.plate_no, v.owner_name, s.slot_code
        FROM parking_sessions ps
        JOIN vehicles v ON ps.vehicle_id = v.vehicle_id
        JOIN slots    s ON ps.slot_id    = s.slot_id
        ORDER BY ps.session_id DESC
        LIMIT ?
    """
    return query_db(sql, (limit,))


def sessions_by_day(days: int = 30) -> list[dict]:
    """Return entry counts per day for the last N days (calendar view data)."""
    return query_db(
        """SELECT date(entry_time) AS day, COUNT(*) AS entries
           FROM parking_sessions
           WHERE date(entry_time) >= date('now','localtime', ? || ' days')
           GROUP BY day
           ORDER BY day""",
        (f"-{days}",),
    )
