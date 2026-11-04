"""Adversarial testing API: queue bounded AI-proposed scenario rounds."""

import json
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Request, status
from app.db import get_db
from app.errors import RoboWitnessException
from app.schemas.adversarial import AdversarialResult, AdversarialTestRequest
from app.schemas.jobs import JobCreateResponse
from app.security import current_workspace

router = APIRouter(prefix="/adversarial-tests", tags=["Adversarial Tests"])


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_adversarial_test(body: AdversarialTestRequest, request: Request):
    if body.seed_run_id:
        with get_db() as conn:
            row = conn.execute(
                "SELECT run_id FROM runs WHERE run_id = ?", (body.seed_run_id,)
            ).fetchone()
        if row is None:
            raise RoboWitnessException(
                status_code=404,
                code="SEED_RUN_NOT_FOUND",
                message=f"Seed run {body.seed_run_id} does not exist",
            )
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    adversarial_id = f"adv-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(
        {
            "policy": body.policy.model_dump(),
            "max_iterations": body.max_iterations,
            "seed_run_id": body.seed_run_id,
            "workspace_id": current_workspace(request),
        }
    )
    with get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, kind, status, payload_json, result_id, "
            "attempts, created_at) VALUES (?, 'adversarial_test', 'queued', ?, ?, 0, ?)",
            (job_id, payload, adversarial_id, now),
        )
        conn.commit()
    return JobCreateResponse(job_id=job_id, result_id=adversarial_id, status="queued")


@router.get("", response_model=List[AdversarialResult], status_code=status.HTTP_200_OK)
def list_adversarial_tests(request: Request, limit: int = 5):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT result_json FROM adversarial_runs WHERE workspace_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (current_workspace(request), max(1, min(limit, 50))),
        ).fetchall()
    return [AdversarialResult.model_validate_json(r["result_json"]) for r in rows]


@router.get("/{adversarial_id}", response_model=AdversarialResult, status_code=status.HTTP_200_OK)
def get_adversarial_test(adversarial_id: str, request: Request):
    with get_db() as conn:
        row = conn.execute(
            "SELECT result_json FROM adversarial_runs WHERE adversarial_id = ? "
            "AND workspace_id = ?",
            (adversarial_id, current_workspace(request)),
        ).fetchone()
    if row is None:
        raise RoboWitnessException(
            status_code=404,
            code="ADVERSARIAL_NOT_FOUND",
            message=f"Adversarial test {adversarial_id} not found (job may still be running)",
        )
    return AdversarialResult.model_validate_json(row["result_json"])
