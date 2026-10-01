"""
tests/test_tqm_modules.py — Unit tests for TQM quality control modules.

Covers:
- Checksheet defect logging, filtering, and status updates.
"""

import pytest
from database.db import init_db, execute_db
from tqm.checksheet import log_defect, get_all_defects, update_defect_status, get_defect_summary


@pytest.fixture(autouse=True)
def setup_tqm():
    """Ensure clean database setup."""
    init_db()


def test_checksheet_lifecycle():
    """Test logging a defect, querying it, and updating its status."""
    defect_id = log_defect(
        module="Entry",
        description="Test queue delay anomaly during peak load",
        fishbone_category="Process",
        defect_type="Queue Delay (> 30s)",
        severity=7,
        is_demo=1,
    )
    assert defect_id > 0

    # Query
    defects = get_all_defects(module="Entry", status="Open")
    assert any(d["defect_id"] == defect_id for d in defects)

    # Update
    update_defect_status(defect_id, "Resolved", "Added automatic bay assignment to clear queue")
    resolved = get_all_defects(status="Resolved")
    target = next((d for d in resolved if d["defect_id"] == defect_id), None)
    assert target is not None
    assert "automatic bay assignment" in target["resolution"]

    # Summary
    summary = get_defect_summary()
    assert summary["total"] >= 1
    assert summary["resolved"] >= 1

    # Cleanup
    execute_db("DELETE FROM defects WHERE defect_id = ?", (defect_id,))
