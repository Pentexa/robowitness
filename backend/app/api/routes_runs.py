"""Runs and Jobs API routes."""
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Query, status
from pydantic import BaseModel
from app.config import settings
from app.db import get_db
from app.errors import RoboWitnessException
from app.schemas.jobs import JobCreateResponse, JobProgress, JobResponse
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.telemetry import RunResult, TelemetryFrame, TelemetryPage

router = APIRouter(tags=["Runs and Jobs"])

class CreateRunRequest(BaseModel):
    scenario: ScenarioSpec
    policy: PolicyConfig

@router.post("/runs", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_run(req: CreateRunRequest):
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    run_id = f"run-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    payload = json.dumps({
        "scenario": req.scenario.model_dump(),
        "policy": req.policy.model_dump(),
        "run_id": run_id,
    })

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (job_id, kind, status, payload_json, result_id, attempts, created_at)
            VALUES (?, 'simulation_run', 'queued', ?, ?, 0, ?)
            """,
            (job_id, payload, run_id, now)
        )
        conn.commit()

    return JobCreateResponse(job_id=job_id, result_id=run_id, status="queued")

@router.get("/jobs/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK)
def get_job(job_id: str):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()

    if not row:
        raise RoboWitnessException(
            status_code=404,
            code="JOB_NOT_FOUND",
            message=f"Job {job_id} does not exist"
        )

    progress = None
    if row["progress_json"]:
        try:
            progress = JobProgress.model_validate_json(row["progress_json"])
        except Exception:
            pass

    return JobResponse(
        job_id=row["job_id"],
        kind=row["kind"],
        status=row["status"],
        progress=progress,
        result_id=row["result_id"],
        error_code=row["error_code"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
    )

@router.post("/jobs/{job_id}/cancel", response_model=JobResponse, status_code=status.HTTP_200_OK)
def cancel_job(job_id: str):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,))
        row = cursor.fetchone()
        if not row:
            raise RoboWitnessException(
                status_code=404,
                code="JOB_NOT_FOUND",
                message=f"Job {job_id} does not exist"
            )

        if row["status"] in ("completed", "failed", "cancelled"):
            return get_job(job_id)

        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "UPDATE jobs SET status = 'cancelled', finished_at = ? WHERE job_id = ?",
            (now, job_id)
        )
        conn.commit()

    return get_job(job_id)

@router.get("/runs/{run_id}", response_model=RunResult, status_code=status.HTTP_200_OK)
def get_run(run_id: str):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,))
        row = cursor.fetchone()

    if not row:
        raise RoboWitnessException(
            status_code=404,
            code="RUN_NOT_FOUND",
            message=f"Run {run_id} does not exist"
        )

    return RunResult(
        run_id=row["run_id"],
        scenario_id="",
        scenario_hash=row["scenario_hash"],
        policy_hash=row["policy_hash"],
        job_status="completed",
        oracle_status=row["oracle_status"],
        reason_codes=json.loads(row["reason_codes_json"]),
        metrics=json.loads(row["metrics_json"]),
        artifact_path=row["artifact_dir"],
        created_at=row["created_at"],
        started_at=None,
        finished_at=row["completed_at"],
    )

@router.get("/runs/{run_id}/telemetry", response_model=TelemetryPage, status_code=status.HTTP_200_OK)
def get_run_telemetry(
    run_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(600, ge=1, le=2000),
):
    run_dir = settings.artifacts_path / "runs" / run_id
    telemetry_file = run_dir / "telemetry.jsonl"
    if not telemetry_file.exists():
        raise RoboWitnessException(
            status_code=404,
            code="TELEMETRY_NOT_FOUND",
            message=f"Telemetry artifact for {run_id} not found on disk"
        )

    frames = []
    total = 0
    with open(telemetry_file, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if not line_str:
                continue
            if total >= offset and len(frames) < limit:
                frames.append(TelemetryFrame.model_validate_json(line_str))
            total += 1

    next_offset = (offset + limit) if (offset + limit) < total else None

    return TelemetryPage(
        run_id=run_id,
        frames=frames,
        total=total,
        offset=offset,
        next_offset=next_offset,
    )
