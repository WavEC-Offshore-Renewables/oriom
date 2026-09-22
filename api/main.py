
import sqlite3
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from api import db
from api.domain.schemas import JobStatus, RunAccepted, RunRequest

app = FastAPI(title="ORIOM API", version="1.0.0")

## To Do - clear this up, messy


def get_row(job_id: str) -> sqlite3.Row:
    row = db.get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No such job: {job_id}")
    return row


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/run", response_model=RunAccepted, status_code=202)
def start_run(request: RunRequest) -> RunAccepted:
    job_id = uuid.uuid4().hex
    db.insert_job(job_id, request.model_dump())

    return RunAccepted(job_id=job_id, status="queued")


@app.get("/runs/{job_id}", response_model=JobStatus)
def get_run(job_id: str) -> JobStatus:
    row = get_row(job_id)

    return JobStatus(
        job_id=row["job_id"],
        status=row["status"],
        detail=row["detail"],
        run_dir=row["run_dir"],
    )


@app.get("/runs/{job_id}/result")
def get_result(job_id: str):
    row = get_row(job_id)

    if row["status"] != "done":
        raise HTTPException(status_code=409, detail=f"Job is {row['status']}, not done.",)

    if not Path(row["zip_path"]).is_file():
        raise HTTPException(status_code=410, detail="Result file no longer available.",)

    return FileResponse(row["zip_path"], media_type="application/zip", filename=f"{job_id}.zip",)


@app.delete("/runs/{job_id}", response_model=JobStatus)
def delete_run(job_id: str) -> JobStatus:
    row = get_row(job_id)

    if row["status"] == "running":
        raise HTTPException(status_code=409, detail="Job is running; wait before deleting.",)

    db.delete_job_data(job_id)
    return JobStatus(job_id=job_id, status="deleted")
