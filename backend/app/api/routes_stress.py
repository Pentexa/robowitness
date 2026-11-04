"""Sensor stress-test API: queue a latency x noise grid over one scenario."""

import json
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Request, status
from app.db import get_db
from app.errors import RoboWitnessException
from app.schemas.jobs import JobCreateResponse
from app.schemas.stress import MAX_CELLS, StressTestRequest, StressTestResult
from app.security import current_workspace

router = APIRouter(prefix="/stress-tests", tags=["Stress Tests"])


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_stress_test(body: StressTestRequest, request: Request):
    latencies = sorted({int(v) for v in body.latencies_ms})
    noises = sorted({float(v) for v in body.noise_levels_m})
    if any(v < 0 or v > 1000 for v in latencies):
        raise RoboWitnessException(
            status_code=422,
            code="STRESS_LATENCY_RANGE",
            message="latencies_ms values must be within 0..1000",
        )
    if any(v < 0.0 or v > 0.2 for v in noises):
        raise RoboWitnessException(
            status_code=422,
            code="STRESS_NOISE_RANGE",
            message="noise_levels_m values must be within 0.0..0.2",
        )
    if len(latencies) * len(noises) > MAX_CELLS:
        raise RoboWitnessException(
            status_code=422,
            code="STRESS_GRID_TOO_LARGE",
            message=f"grid has {len(latencies) * len(noises)} cells; max is {MAX_CELLS}",
        )
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    stress_id = f"stress-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(
        {
            "scenario": body.scenario.model_dump(),
            "policy": body.policy.model_dump(),
            "latencies_ms": latencies,
            "noise_levels_m": noises,
            "workspace_id": current_workspace(request),
        }
    )
    with get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, kind, status, payload_json, result_id, "
            "attempts, created_at) VALUES (?, 'stress_test', 'queued', ?, ?, 0, ?)",
            (job_id, payload, stress_id, now),
        )
        conn.commit()
    return JobCreateResponse(job_id=job_id, result_id=stress_id, status="queued")


def _load(stress_id: str, workspace: str) -> StressTestResult:
    with get_db() as conn:
        row = conn.execute(
            "SELECT result_json FROM stress_runs WHERE stress_id = ? AND workspace_id = ?",
            (stress_id, workspace),
        ).fetchone()
    if row is None:
        raise RoboWitnessException(
            status_code=404,
            code="STRESS_NOT_FOUND",
            message=f"Stress test {stress_id} not found (job may still be running)",
        )
    return StressTestResult.model_validate_json(row["result_json"])


@router.get("", response_model=List[StressTestResult], status_code=status.HTTP_200_OK)
def list_stress_tests(request: Request, limit: int = 5):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT result_json FROM stress_runs WHERE workspace_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (current_workspace(request), max(1, min(limit, 50))),
        ).fetchall()
    return [StressTestResult.model_validate_json(r["result_json"]) for r in rows]


@router.get("/{stress_id}", response_model=StressTestResult, status_code=status.HTTP_200_OK)
def get_stress_test(stress_id: str, request: Request):
    return _load(stress_id, current_workspace(request))
