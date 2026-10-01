"""
tests/test_ui_smoke.py — Streamlit AppTest smoke tests.

Verifies that app.py loads, initializes database state, and renders the router
without throwing any unhandled exceptions.
"""

import os
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


def test_app_loads_without_exceptions():
    """Verify that app.py boots and executes without throwing unhandled exceptions."""
    at = AppTest.from_file(APP_PATH, default_timeout=30)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
