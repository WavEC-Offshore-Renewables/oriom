"""Start queued simulations, at most ORIOM_MAX_RUNNING at a time.

Runs forever as its own process next to the API (see start.sh). Each loop it
starts workers for queued jobs while slots are free, marks jobs whose worker
process vanished as failed, and deletes the files of jobs older than
ORIOM_KEEP_DAYS that DRF never collected.
"""
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from api import db

MAX_RUNNING = int(os.environ.get("ORIOM_MAX_RUNNING", "4"))
POLL_SECONDS = float(os.environ.get("ORIOM_POLL_SECONDS", "3"))
KEEP_DAYS = int(os.environ.get("ORIOM_KEEP_DAYS", "7"))

# Live Popen handles for workers this dispatcher started; poll() reaps them.
procs: dict[str, subprocess.Popen] = {}


def start_queued() -> None:
    with db.connect() as conn:
        running = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status = 'running'"
        ).fetchone()[0]

        queued = conn.execute(
            "SELECT job_id FROM jobs WHERE status = 'queued' "
            "ORDER BY created_at LIMIT ?",
            (max(MAX_RUNNING - running, 0),),
        ).fetchall()

    for row in queued:
        job_id = row["job_id"]
        db.LOGS_DIR.mkdir(parents=True, exist_ok=True)

        proc = subprocess.Popen(
            [sys.executable, "-m", "api.domain.worker", job_id],
            stdout=(db.LOGS_DIR / f"{job_id}.log").open("w"),
            stderr=subprocess.STDOUT,
        )
        procs[job_id] = proc
        db.update_job(job_id, status="running", pid=proc.pid)
        logging.info("started job %s (pid %s)", job_id, proc.pid)


def reap_dead() -> None:
    for job_id, proc in list(procs.items()):
        if proc.poll() is not None:
            del procs[job_id]

    with db.connect() as conn:
        # A row still 'running' whose worker is gone was killed hard (or died
        # with a previous container); the worker writes done/failed itself on
        # any normal exit. The status guard keeps this from racing that write.
        for row in conn.execute(
            "SELECT job_id, request FROM jobs WHERE status = 'running'"
        ).fetchall():
            if row["job_id"] not in procs:
                # Record the partial run folder (named after the job id) so
                # the cleanup sweep can remove it later.
                farm_id = json.loads(row["request"])["farm_id"]
                leftovers = sorted(
                    Path.cwd().glob(f"tmp/{farm_id}_{row['job_id'][:8]}_*")
                )
                conn.execute(
                    "UPDATE jobs SET status = 'failed', detail = ?, "
                    "run_dir = ?, finished_at = datetime('now') "
                    "WHERE job_id = ? AND status = 'running'",
                    (
                        "Worker process died.",
                        str(leftovers[0]) if leftovers else None,
                        row["job_id"],
                    ),
                )


def cleanup_old() -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)

    with db.connect() as conn:
        rows = conn.execute(
            "SELECT job_id FROM jobs WHERE status IN ('done', 'failed') "
            "AND finished_at < ?",
            (cutoff.strftime("%Y-%m-%d %H:%M:%S"),),
        ).fetchall()

    for row in rows:
        logging.info("cleaning up uncollected job %s", row["job_id"])
        db.delete_job_data(row["job_id"])


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    logging.info("dispatcher up: max %s parallel runs", MAX_RUNNING)

    while True:
        reap_dead()
        start_queued()
        cleanup_old()
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
