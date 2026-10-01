"""
modules/billing.py — Fee calculation for parking sessions.

Formula (from the SRS FR-14):
  if duration_minutes <= free_minutes:
      fee = base_rate
  else:
      billable_minutes = duration_minutes - free_minutes
      full_hours = ceil(billable_minutes / 60)
      fee = base_rate + full_hours * per_hour_rate

Why explicit math.ceil: Python's integer division truncates; parking operators
always round UP to the next full hour (industry standard, stated in config).
"""

import math
from datetime import datetime
from database.db import query_db


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_tariff(vehicle_type: str) -> dict | None:
    """Fetch the tariff row for a given vehicle type from the DB.

    Returns None if the vehicle type has no tariff configured.
    """
    rows = query_db(
        "SELECT * FROM tariff WHERE vehicle_type = ?",
        (vehicle_type,),
    )
    return rows[0] if rows else None


def get_all_tariffs() -> list[dict]:
    """Return all tariff rows (for the settings/tariff management page)."""
    return query_db("SELECT * FROM tariff ORDER BY vehicle_type")


def calculate_duration_minutes(entry_time: str, exit_time: str) -> float:
    """Return the parking duration in minutes between two ISO datetime strings.

    Args:
        entry_time: ISO datetime string, e.g. '2026-09-30 10:15:00'.
        exit_time:  ISO datetime string, e.g. '2026-09-30 12:45:00'.

    Returns:
        Duration in decimal minutes (can be fractional).

    Raises:
        ValueError: If exit_time is before or equal to entry_time.
    """
    fmt = TIME_FORMAT
    t_entry = datetime.strptime(entry_time, fmt)
    t_exit  = datetime.strptime(exit_time,  fmt)
    delta   = t_exit - t_entry
    if delta.total_seconds() <= 0:
        raise ValueError(
            "Exit time must be after entry time.  "
            f"Entry: {entry_time} | Exit: {exit_time}"
        )
    return delta.total_seconds() / 60.0


def calculate_fee(vehicle_type: str, duration_minutes: float) -> float:
    """Compute the parking fee for a given vehicle type and duration.

    Args:
        vehicle_type:     One of 'Car', 'Bike', 'EV'.
        duration_minutes: Total duration in minutes (from calculate_duration_minutes).

    Returns:
        Fee in Indian Rupees, rounded to 2 decimal places.

    Raises:
        ValueError: If no tariff is configured for the vehicle type.
    """
    tariff = get_tariff(vehicle_type)
    if tariff is None:
        raise ValueError(
            f"No tariff found for vehicle type '{vehicle_type}'. "
            "Please configure the tariff in the database."
        )

    base_rate     = tariff["base_rate"]
    per_hour_rate = tariff["per_hour_rate"]
    free_minutes  = tariff["free_minutes"]

    if duration_minutes <= free_minutes:
        fee = base_rate
    else:
        billable_minutes = duration_minutes - free_minutes
        full_hours       = math.ceil(billable_minutes / 60)
        fee              = base_rate + full_hours * per_hour_rate

    return round(fee, 2)


def revenue_today() -> float:
    """Return total fee collected from sessions completed today."""
    rows = query_db(
        """SELECT COALESCE(SUM(fee), 0) AS total
           FROM parking_sessions
           WHERE status = 'Completed'
             AND date(exit_time) = date('now','localtime')"""
    )
    return round(rows[0]["total"], 2) if rows else 0.0


def revenue_by_day(days: int = 30) -> list[dict]:
    """Return daily revenue for the last N days, suitable for chart rendering."""
    return query_db(
        """SELECT date(exit_time) AS day, ROUND(SUM(fee),2) AS total
           FROM parking_sessions
           WHERE status='Completed'
             AND exit_time IS NOT NULL
             AND date(exit_time) >= date('now','localtime', ? || ' days')
           GROUP BY day
           ORDER BY day""",
        (f"-{days}",),
    )
