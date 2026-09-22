"""sqlite bookkeeping for simulation jobs.

One row per job. The API workers, the dispatcher and the simulation workers
are separate processes, so every access opens its own short-lived connection;
WAL mode plus a busy timeout let them share the file safely.
"""
import json
import os
import shutil
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("ORIOM_DB_PATH", Path.cwd() / "tmp" / "jobs.db"))

LOGS_DIR = DB_PATH.parent / "logs"
ZIPS_DIR = DB_PATH.parent / "results"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id      TEXT PRIMARY KEY,
    request     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'queued',
    detail      TEXT,
    run_dir     TEXT,
    zip_path    TEXT,
    pid         INTEGER,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT
)
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=30000")
    conn.execute(SCHEMA)
    return conn


def insert_job(job_id: str, request: dict) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, request) VALUES (?, ?)",
            (job_id, json.dumps(request)),
        )


def get_job(job_id: str) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()


def update_job(job_id: str, **fields) -> None:
    columns = ", ".join(f"{key} = ?" for key in fields)
    with connect() as conn:
        conn.execute(
            f"UPDATE jobs SET {columns} WHERE job_id = ?",
            (*fields.values(), job_id),
        )


def finish_job(job_id: str, **fields) -> None:
    """Record a job's final state, but only if it is still running.

    The guard keeps a finishing worker from overwriting a row that was
    deleted (or reaped) while the simulation ran.
    """
    columns = ", ".join(f"{key} = ?" for key in fields)
    with connect() as conn:
        conn.execute(
            f"UPDATE jobs SET {columns} WHERE job_id = ? AND status = 'running'",
            (*fields.values(), job_id),
        )


def delete_job_data(job_id: str) -> None:
    """Remove a job's files (run folders, zip, log) and mark the row deleted."""
    row = get_job(job_id)

    if row["run_dir"]:
        shutil.rmtree(row["run_dir"], ignore_errors=True)
    if row["zip_path"]:
        Path(row["zip_path"]).unlink(missing_ok=True)
    (LOGS_DIR / f"{job_id}.log").unlink(missing_ok=True)

    update_job(job_id, status="deleted", run_dir=None, zip_path=None)
