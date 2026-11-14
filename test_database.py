
import pytest

from src import database


@pytest.fixture
def test_database(tmp_path, monkeypatch):

    # Use a temporary database instead of actual project DB
    test_db_path = tmp_path / "test_bug_finder.db"

    monkeypatch.setattr(
        database,
        "DB_PATH",
        test_db_path
    )

    database.initialize_database()

    return test_db_path


def sample_result(count, severity="ERROR"):

    return {
        "fingerprint": "abc123",
        "normalized_error": "Database connection failed",
        "count": count,
        "severity": severity,
        "first_seen": "2026-11-14 10:00:01",
        "last_seen": "2026-11-14 10:05:01",
        "examples": ["ERROR Database connection failed"],
        "ai_analysis": None,
        "analysis_status": "FAILED",
        "analysis_error": "Test analysis failure"
    }


def test_database_initialization(test_database):

    assert test_database.exists()


def test_save_and_retrieve_scan(test_database):

    results = [
        sample_result(3)
    ]

    scan_id = database.save_scan_results(
        "application.log",
        results
    )

    history = database.get_scan_history()

    assert scan_id == 1
    assert len(history) == 1
    assert history[0]["total_unique_error_groups"] == 1
    assert history[0]["total_error_occurrences"] == 3


def test_recurring_error_increasing_trend(test_database):

    # First scan: 2 occurrences
    database.save_scan_results(
        "application.log",
        [sample_result(2, "ERROR")]
    )

    # Second scan: 5 occurrences
    database.save_scan_results(
        "application.log",
        [sample_result(5, "CRITICAL")]
    )

    recurring = database.get_recurring_errors()

    assert len(recurring) == 1

    error = recurring[0]

    assert error["scan_count"] == 2
    assert error["total_occurrences"] == 7
    assert error["previous_scan_count"] == 2
    assert error["latest_scan_count"] == 5
    assert error["trend"] == "INCREASING"
    assert error["highest_severity"] == "CRITICAL"


def test_recurring_error_resolved_trend(test_database):

    # Scan 1: error occurs 4 times
    database.save_scan_results(
        "application.log",
        [sample_result(4)]
    )

    # Scan 2: same error occurs 2 times
    database.save_scan_results(
        "application.log",
        [sample_result(2)]
    )

    # Scan 3: original error is absent
    another_error = sample_result(3)
    another_error["fingerprint"] = "xyz456"
    another_error["normalized_error"] = "Authentication failed"

    database.save_scan_results(
        "application.log",
        [another_error]
    )

    recurring = database.get_recurring_errors()

    assert len(recurring) == 1

    error = recurring[0]

    assert error["fingerprint"] == "abc123"
    assert error["scan_count"] == 2
    assert error["previous_scan_count"] == 2
    assert error["latest_scan_count"] == 0
    assert error["trend"] == "RESOLVED"
