"""
modules/validation.py — Poka-Yoke (mistake-proofing) input validators.

Every public function returns (True, "") on success or (False, error_message)
on failure.  Callers display the error message directly — no raw exceptions
reach the UI.

Why Poka-Yoke? It is a TQM technique that prevents errors at the source.
Here we prevent: bad plates, bad phones, empty names, double entries, and
exit-before-entry — the most common data integrity failures in a parking system.
"""

import re
from config import PLATE_REGEX, PHONE_DIGITS


def validate_plate(plate_no: str) -> tuple[bool, str]:
    """Validate an Indian vehicle plate number format.

    Valid format: 2 uppercase letters + 2 digits + 1-2 uppercase letters + 4 digits
    Examples: UK07AB1234, DL01X5678 (also accepted: DL01AB5678)

    Returns:
        (True, "")  if valid.
        (False, message) if invalid.
    """
    plate = plate_no.strip().upper()
    if not plate:
        return False, "Plate number cannot be empty."
    if not re.match(PLATE_REGEX, plate):
        return False, (
            f"'{plate}' is not a valid Indian plate number.  "
            "Expected format: 2 letters + 2 digits + 1-2 letters + 4 digits "
            "(e.g. UK07AB1234)."
        )
    return True, ""


def validate_phone(phone: str) -> tuple[bool, str]:
    """Validate that the phone number contains exactly 10 digits.

    Returns:
        (True, "")  if valid.
        (False, message) if invalid.
    """
    digits = re.sub(r"\D", "", phone.strip())  # strip non-digits (spaces, dashes)
    if len(digits) != PHONE_DIGITS:
        return False, (
            f"Phone number must contain exactly {PHONE_DIGITS} digits. "
            f"Got {len(digits)} digits in '{phone}'."
        )
    return True, ""


def validate_non_empty(value: str, field_name: str) -> tuple[bool, str]:
    """Validate that a required text field is not blank.

    Returns:
        (True, "")  if value is non-empty after stripping whitespace.
        (False, message) if blank.
    """
    if not value or not value.strip():
        return False, f"'{field_name}' cannot be empty."
    return True, ""


def validate_exit_after_entry(entry_time: str, exit_time: str) -> tuple[bool, str]:
    """Validate that exit_time is strictly after entry_time.

    Both strings must be in 'YYYY-MM-DD HH:MM:SS' format.

    Returns:
        (True, "")  if exit is after entry.
        (False, message) if not.
    """
    from datetime import datetime
    fmt = "%Y-%m-%d %H:%M:%S"
    try:
        t_entry = datetime.strptime(entry_time, fmt)
        t_exit  = datetime.strptime(exit_time,  fmt)
    except ValueError as exc:
        return False, f"Invalid datetime format: {exc}"
    if t_exit <= t_entry:
        return False, (
            f"Exit time ({exit_time}) must be after entry time ({entry_time}).  "
            "Cannot record an exit before or at the moment of entry."
        )
    return True, ""


def validate_slot_available(slot: dict) -> tuple[bool, str]:
    """Validate that a slot is Available before assigning it to a vehicle.

    Args:
        slot: A slot dict with at least 'status' and 'slot_code' keys.

    Returns:
        (True, "")  if Available.
        (False, message) if Occupied or Maintenance.
    """
    if slot["status"] != "Available":
        return False, (
            f"Slot '{slot['slot_code']}' is currently '{slot['status']}' "
            "and cannot be assigned.  Choose a different slot."
        )
    return True, ""


def validate_vehicle_form(plate_no: str, owner_name: str,
                           phone: str) -> tuple[bool, str]:
    """Run all vehicle registration validators in sequence.

    Returns the first failure found, or (True, "") if all pass.
    """
    for ok, msg in [
        validate_non_empty(plate_no,    "Plate Number"),
        validate_plate(plate_no),
        validate_non_empty(owner_name,  "Owner Name"),
        validate_non_empty(phone,       "Phone Number"),
        validate_phone(phone),
    ]:
        if not ok:
            return False, msg
    return True, ""
