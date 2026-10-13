"""
db.py -- SQLite run log for LineaScope.

Only the `run` table is stored in SQLite. Candidate segments, detections
and reference lineaments stay in files (Parquet, GeoJSON) because they
are large or spatial. This matches Section 3.6 of the project report.

Schema:
    run (
        run_id          TEXT PRIMARY KEY
        started_at      TEXT (ISO 8601 UTC)
        threshold       REAL
        min_length_m    INTEGER
        n_lineaments    INTEGER
        total_length_km REAL
        runtime_s       REAL
        git_commit      TEXT
        parameters      TEXT (JSON)
    )
"""

import json
import sqlite3
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.config import METADATA


DB_PATH = METADATA / "lineascope.db"


def _get_git_commit() -> str:
    """Best-effort short git commit; returns 'unknown' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent.parent,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def init_db() -> None:
    """Create the database file and tables if they do not exist."""
    METADATA.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS run (
                run_id          TEXT PRIMARY KEY,
                started_at      TEXT NOT NULL,
                threshold       REAL NOT NULL,
                min_length_m    INTEGER NOT NULL,
                n_lineaments    INTEGER NOT NULL,
                total_length_km REAL NOT NULL,
                runtime_s       REAL NOT NULL,
                git_commit      TEXT NOT NULL,
                parameters      TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_run_started_at "
            "ON run(started_at DESC)"
        )
        conn.commit()


def insert_run(
    threshold: float,
    min_length_m: int,
    n_lineaments: int,
    total_length_km: float,
    runtime_s: float,
) -> str:
    """Insert a run record. Returns the generated run_id."""
    run_id = (
        f"run_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_"
        f"{uuid.uuid4().hex[:6]}"
    )
    started_at = datetime.now(timezone.utc).isoformat()
    git_commit = _get_git_commit()
    parameters = json.dumps(
        {"threshold": float(threshold), "min_length_m": int(min_length_m)}
    )

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO run (
                run_id, started_at, threshold, min_length_m,
                n_lineaments, total_length_km, runtime_s,
                git_commit, parameters
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                started_at,
                float(threshold),
                int(min_length_m),
                int(n_lineaments),
                float(total_length_km),
                float(runtime_s),
                git_commit,
                parameters,
            ),
        )
        conn.commit()
    return run_id


def list_runs(limit: int = 10) -> list:
    """Return the most recent runs, newest first."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT run_id, started_at, threshold, min_length_m,
                   n_lineaments, total_length_km, runtime_s, git_commit
            FROM run
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(r) for r in rows]


def count_runs() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        (n,) = conn.execute("SELECT COUNT(*) FROM run").fetchone()
    return int(n)