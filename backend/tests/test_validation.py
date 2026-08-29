import pytest
from datetime import date
from backend.app.services.validation import (
    validate_date_range,
    validate_percent_complete,
    validate_duplicate_activity_ids,
    ValidationError
)

def test_invalid_date_range():
    # planned_finish < planned_start should raise ValidationError
    start = date(2026, 6, 10)
    finish = date(2026, 6, 1)
    with pytest.raises(ValidationError) as exc:
        validate_date_range(start, finish)
    assert "Invalid date range" in str(exc.value)

def test_invalid_percent_complete():
    # Negative percentage
    with pytest.raises(ValidationError):
        validate_percent_complete(-10.0)
    # Exceeding 100%
    with pytest.raises(ValidationError):
        validate_percent_complete(150.0)
    # Valid percentages should pass
    validate_percent_complete(0.0)
    validate_percent_complete(50.5)
    validate_percent_complete(100.0)

def test_duplicate_activity_detection():
    ids = ["ACT-001", "ACT-002", "ACT-001"]
    with pytest.raises(ValidationError) as exc:
        validate_duplicate_activity_ids(ids)
    assert "Duplicate activity IDs detected" in str(exc.value)
