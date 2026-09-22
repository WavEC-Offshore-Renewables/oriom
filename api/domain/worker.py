"""Run exactly one ORIOM simulation, then exit.

Invoked as ``python -m api.domain.worker <job_id>``. This runs as its own process on
purpose: adapter.install() rebinds a module global in ``oriom.main``, so two
simulations sharing a process would collide.
"""
import json
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from api import db


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def zip_result(result_dir: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in result_dir.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(result_dir.parent))


def main(job_id: str) -> int:
    payload = json.loads(db.get_job(job_id)["request"])

    try:
        from api.domain import adapter, config

        adapter.install(payload)

        import oriom.main

        dirs = oriom.main.run(config.build_config(payload["farm_id"], job_id))

        # Deliver only the averaged results (~1 MB); export_pack is not shipped.
        zip_path = db.ZIPS_DIR / f"{job_id}.zip"
        zip_result(Path(dirs.run_dir) / "result_dir_avg", zip_path)
    except Exception as exc:
        traceback.print_exc()
        # The run folder embeds the job id (config.build_config), so a failed
        # run's partial output can still be recorded for later cleanup.
        leftovers = sorted(
            Path.cwd().glob(f"tmp/{payload['farm_id']}_{job_id[:8]}_*")
        )
        db.finish_job(
            job_id,
            status="failed",
            detail=f"{type(exc).__name__}: {exc}",
            run_dir=str(leftovers[0]) if leftovers else None,
            finished_at=now(),
        )
        return 1

    db.finish_job(
        job_id,
        status="done",
        run_dir=str(dirs.run_dir),
        zip_path=str(zip_path),
        finished_at=now(),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
