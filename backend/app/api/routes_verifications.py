"""Independent Verification API routes."""

import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Query, status
from app.config import settings
from app.db import get_db
from app.errors import RoboWitnessException
from app.schemas.jobs import JobCreateResponse
from typing import List

from app.schemas.telemetry import TelemetryFrame, TelemetryPage
from app.schemas.verification import (
    VerificationRecord,
    VerificationSummary,
    VerifyFixRequest,
)

router = APIRouter(tags=["Verifications"])


@router.post(
    "/fixes/verify",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def verify_candidate_fix(req: VerifyFixRequest):
    with get_db() as conn:
        cursor = conn.execute("SELECT run_id FROM runs WHERE run_id = ?", (req.baseline_run_id,))
        if not cursor.fetchone():
            raise RoboWitnessException(
                status_code=404,
                code="BASELINE_RUN_NOT_FOUND",
                message=f"Baseline run {req.baseline_run_id} does not exist",
            )
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    verification_id = f"verif-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    payload = json.dumps(
        {
            "baseline_run_id": req.baseline_run_id,
            "candidate_policy": req.candidate_policy.model_dump(),
            "verification_id": verification_id,
        }
    )

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (job_id, kind, status, payload_json, result_id, attempts, created_at)
            VALUES (?, 'verification', 'queued', ?, ?, 0, ?)
            """,
            (job_id, payload, verification_id, now),
        )
        conn.commit()

    return JobCreateResponse(job_id=job_id, result_id=verification_id, status="queued")


@router.get(
    "/verifications",
    response_model=List[VerificationSummary],
    status_code=status.HTTP_200_OK,
)
def list_verifications(limit: int = Query(10, ge=1, le=50)):
    """Newest verification summaries for the history picker (no telemetry)."""
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT verification_id, verdict, baseline_run_id, created_at, completed_at"
            " FROM verifications ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = cursor.fetchall()
    return [
        VerificationSummary(
            verification_id=r["verification_id"],
            verdict=r["verdict"],
            baseline_run_id=r["baseline_run_id"],
            created_at=r["created_at"],
            completed_at=r["completed_at"],
        )
        for r in rows
    ]


@router.get(
    "/verifications/{verification_id}",
    response_model=VerificationRecord,
    status_code=status.HTTP_200_OK,
)
def get_verification(verification_id: str):
    with get_db() as conn:
        cursor = conn.execute(
            "SELECT * FROM verifications WHERE verification_id = ?", (verification_id,)
        )
        row = cursor.fetchone()

    if not row:
        raise RoboWitnessException(
            status_code=404,
            code="VERIFICATION_NOT_FOUND",
            message=f"Verification {verification_id} does not exist",
        )

    return VerificationRecord(
        verification_id=row["verification_id"],
        job_id=row["job_id"],
        baseline_run_id=row["baseline_run_id"],
        candidate_policy=json.loads(row["candidate_policy_json"]),
        verdict=row["verdict"],
        gates=json.loads(row["gates_json"]),
        reason_codes=[],
        artifact_dir=row["artifact_dir"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
    )


@router.get(
    "/verifications/{verification_id}/candidate-telemetry",
    response_model=TelemetryPage,
    status_code=status.HTTP_200_OK,
)
def get_candidate_telemetry(
    verification_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(600, ge=1, le=2000),
):
    """Paginated paired-candidate frames sealed with the verification package.

    Packages created before candidate replay existed return 404; their gate
    metrics in comparison.json remain the source of truth.
    """
    v_dir = settings.artifacts_path / "verifications" / verification_id
    try:
        resolved = v_dir.resolve()
        if str(resolved) != str(
            (settings.artifacts_path / "verifications" / verification_id).resolve()
        ):
            raise RoboWitnessException(
                status_code=403, code="FORBIDDEN_PATH", message="Access denied"
            )
    except RoboWitnessException:
        raise
    except Exception:
        raise RoboWitnessException(status_code=403, code="FORBIDDEN_PATH", message="Access denied")

    telemetry_file = resolved / "telemetry_candidate.jsonl"
    if not telemetry_file.exists():
        raise RoboWitnessException(
            status_code=404,
            code="CANDIDATE_TELEMETRY_NOT_FOUND",
            message=(
                f"No sealed candidate replay for {verification_id} "
                "(older package or incomplete run)"
            ),
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
        run_id=verification_id,
        frames=frames,
        total=total,
        offset=offset,
        next_offset=next_offset,
    )
