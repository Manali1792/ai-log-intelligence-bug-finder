import sqlite3
import json
from pathlib import Path

# Keep database in project root, regardless of working directory
DB_PATH = Path(__file__).resolve().parent.parent / "bug_finder.db"

def get_connection():

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row   #it will allow to access database records in dictionary format ,
    # for db we need to write row[0] but now we can write 
    # row["severity"]

    # Enable foreign key constraints
    connection.execute("PRAGMA foreign_keys = ON")

    return connection

def initialize_database():
    """Create database tables if they do not exist."""

    with get_connection() as connection:

        # Table 1: Every execution of Bug Finder
        connection.execute("""
            CREATE TABLE IF NOT EXISTS scan_runs (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                source_file TEXT NOT NULL,

                scanned_at TEXT DEFAULT CURRENT_TIMESTAMP,

                total_unique_error_groups INTEGER DEFAULT 0,

                total_error_occurrences INTEGER DEFAULT 0,

                successful_analyses INTEGER DEFAULT 0
            )
        """)

        # Table 2: Error groups belonging to each scan
        connection.execute("""
            CREATE TABLE IF NOT EXISTS error_groups (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                scan_id INTEGER NOT NULL,

                fingerprint TEXT NOT NULL,

                normalized_error TEXT NOT NULL,

                count INTEGER DEFAULT 0,

                severity TEXT NOT NULL,

                first_seen TEXT,

                last_seen TEXT,

                examples TEXT,

                ai_analysis TEXT,

                analysis_status TEXT,

                analysis_error TEXT,

                FOREIGN KEY (scan_id)
                    REFERENCES scan_runs(id),

                UNIQUE(scan_id, fingerprint)
            )
        """)

        # Indexes make historical lookups faster
        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_error_fingerprint
            ON error_groups(fingerprint)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_scan_date
            ON scan_runs(scanned_at)
        """)


def save_scan_results(source_file: str, results: list[dict]):
    """Save a complete scan and its error groups."""

    total_occurrences = sum(
        item["count"] for item in results
    )

    successful_analyses = sum(
        1 for item in results
        if item["analysis_status"] == "SUCCESS"
    )

    with get_connection() as connection:

        cursor = connection.execute(
            """
            INSERT INTO scan_runs (
                source_file,
                total_unique_error_groups,
                total_error_occurrences,
                successful_analyses
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                source_file,
                len(results),
                total_occurrences,
                successful_analyses
            )
        )

        scan_id = cursor.lastrowid

        for item in results:

            connection.execute(
                """
                INSERT INTO error_groups (
                    scan_id,
                    fingerprint,
                    normalized_error,
                    count,
                    severity,
                    first_seen,
                    last_seen,
                    examples,
                    ai_analysis,
                    analysis_status,
                    analysis_error
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_id,
                    item["fingerprint"],
                    item["normalized_error"],
                    item["count"],
                    item["severity"],
                    item["first_seen"],
                    item["last_seen"],
                    json.dumps(item["examples"]),
                    json.dumps(item.get("ai_analysis"))
                    if item.get("ai_analysis") is not None
                    else None,
                    item["analysis_status"],
                    item.get("analysis_error")
                )
            )

    return scan_id


def get_scan_history(limit: int = 10):
    """Retrieve the most recent scan records."""

    with get_connection() as connection:

        rows = connection.execute(
            """
            SELECT *
            FROM scan_runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

    return [dict(row) for row in rows]


def get_recurring_errors():
    """Find recurring errors and analyze their occurrence trends."""

    severity_priority = {
        "ERROR": 1,
        "CRITICAL": 2,
        "FATAL": 3
    }

    with get_connection() as connection:

        # Get the IDs of the latest two recorded scans
        scan_rows = connection.execute(
            """
            SELECT id
            FROM scan_runs
            ORDER BY id DESC
            LIMIT 2
            """
        ).fetchall()

        latest_scan_ids = [
            row["id"] for row in scan_rows
        ]

        # Get all error records from historical scans
        rows = connection.execute(
            """
            SELECT
                fingerprint,
                normalized_error,
                scan_id,
                count,
                severity
            FROM error_groups
            ORDER BY scan_id ASC
            """
        ).fetchall()

    # Group records using fingerprint
    grouped_errors = {}

    for row in rows:

        key = (
            row["fingerprint"],
            row["normalized_error"]
        )

        if key not in grouped_errors:
            grouped_errors[key] = {
                "fingerprint": row["fingerprint"],
                "normalized_error": row["normalized_error"],
                "scan_counts": {},
                "scan_ids": set(),
                "total_occurrences": 0,
                "highest_severity": "ERROR"
            }

        group = grouped_errors[key]

        group["scan_ids"].add(row["scan_id"])

        group["scan_counts"][row["scan_id"]] = row["count"]

        group["total_occurrences"] += row["count"]

        # Determine actual highest severity
        if (
            severity_priority[row["severity"]]
            >
            severity_priority[group["highest_severity"]]
        ):
            group["highest_severity"] = row["severity"]

    recurring_errors = []

    for group in grouped_errors.values():

        # Ignore errors found in only one scan
        if len(group["scan_ids"]) <= 1:
            continue

        previous_count = 0
        latest_count = 0

        if len(latest_scan_ids) >= 2:

            latest_scan_id = latest_scan_ids[0]
            previous_scan_id = latest_scan_ids[1]

            previous_count = group["scan_counts"].get(
                previous_scan_id, 0
            )

            latest_count = group["scan_counts"].get(
                latest_scan_id, 0
            )

        # Determine occurrence trend
        if latest_count > previous_count:
            trend = "INCREASING"

        elif latest_count == 0 and previous_count > 0:
            trend = "RESOLVED"

        elif latest_count < previous_count:
            trend = "DECREASING"

        else:
            trend = "STABLE"

        recurring_errors.append({
            "fingerprint": group["fingerprint"],
            "normalized_error": group["normalized_error"],
            "scan_count": len(group["scan_ids"]),
            "total_occurrences": group["total_occurrences"],
            "highest_severity": group["highest_severity"],
            "previous_scan_count": previous_count,
            "latest_scan_count": latest_count,
            "trend": trend
        })

    return sorted(
        recurring_errors,
        key=lambda item: item["total_occurrences"],
        reverse=True
    )
