"""
config.py — Central configuration for the Parking Management System.

All tunable constants live here so nothing is hardcoded in modules.
Import this file; never import from modules into this file (avoids circular deps).
"""

import os

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Resolve path relative to this file so the app works regardless of cwd.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "parking.db")
SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")

# ---------------------------------------------------------------------------
# Parking slot types and vehicle types
# ---------------------------------------------------------------------------

SLOT_TYPES = ["Car", "Bike", "EV", "Disabled"]
VEHICLE_TYPES = ["Car", "Bike", "EV"]
SLOT_STATUSES = ["Available", "Occupied", "Maintenance"]
SESSION_STATUSES = ["Active", "Completed"]

# ---------------------------------------------------------------------------
# Default tariff (used only by seed.py — live tariff is stored in the DB)
# ---------------------------------------------------------------------------

DEFAULT_TARIFF = {
    #  vehicle_type: (base_rate ₹, per_hour_rate ₹, free_minutes)
    "Car":  (20.0, 30.0, 15),
    "Bike": (10.0, 15.0, 15),
    "EV":   (15.0, 20.0, 30),
}

# ---------------------------------------------------------------------------
# Defect / FMEA categories
# ---------------------------------------------------------------------------

FISHBONE_CATEGORIES = ["People", "Process", "Software Code", "Infrastructure"]
DEFECT_SEVERITIES = list(range(1, 11))   # 1 (minor) to 10 (catastrophic)
DEFECT_STATUSES = ["Open", "In Progress", "Resolved"]

# ---------------------------------------------------------------------------
# Theme palettes  (name: {bg, surface, primary, text, chart_color})
# ---------------------------------------------------------------------------

THEME_PALETTES = {
    "Ocean": {
        "bg": "#0d1b2a",
        "surface": "#1b2a3b",
        "primary": "#00b4d8",
        "text": "#e0f4ff",
        "chart": "#00b4d8",
    },
    "Forest": {
        "bg": "#0f2613",
        "surface": "#1a3a1f",
        "primary": "#52b788",
        "text": "#d8f3dc",
        "chart": "#52b788",
    },
    "Sunset": {
        "bg": "#2b1a0f",
        "surface": "#3d2610",
        "primary": "#f4845f",
        "text": "#fff1e6",
        "chart": "#f4845f",
    },
    "Royal": {
        "bg": "#1a0a2e",
        "surface": "#2a1550",
        "primary": "#9d4edd",
        "text": "#f0e6ff",
        "chart": "#9d4edd",
    },
    "Slate": {
        "bg": "#1c1f26",
        "surface": "#2a2d36",
        "primary": "#7eb8f7",
        "text": "#e8eaf0",
        "chart": "#7eb8f7",
    },
}

PALETTE_NAMES = list(THEME_PALETTES.keys())
DEFAULT_PALETTE = "Ocean"
DEFAULT_DARK_MODE = True  # start in dark mode by default

# ---------------------------------------------------------------------------
# Zones (used by seed.py and slot CRUD defaults)
# ---------------------------------------------------------------------------

PARKING_ZONES = ["A", "B", "C", "D"]

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Indian vehicle plate regex:  AA00AA0000  (state code + RTO + series + number)
PLATE_REGEX = r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$"
PHONE_DIGITS = 10
