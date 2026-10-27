"""Independent Verification API routes."""
import json
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.config import settings
from app.db import get_db
from app.errors import RoboWitnessException
from app.schemas.jobs import JobCreateResponse
from app.schemas.verification import GateResult, VerificationRecord, VerifyFixRequest

router = APIRouter(tags=["Verifications"])

@router.post("/fixes/verify", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def verify_candidate_fix(req: VerifyFixRequest):
    job_id = f"job-{uuid.uuid4().hex[:12]}"
    verification_id = f"verif-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    payload = json.dumps({
        "baseline_run_id": req.baseline_run_id,
        "candidate_policy": req.candidate_policy.model_dump(),
        "verification_id": verification_id,
    })

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO jobs (job_id, kind, status, payload_json, result_id, attempts, created_at)
            VALUES (?, 'verification', 'queued', ?, ?, 0, ?)
            """,
            (job_id, payload, verification_id, now)
        )
        conn.commit()

    return JobCreateResponse(job_id=job_id, result_id=verification_id, status="queued")

@router.get("/verifications/{verification_id}", response_model=VerificationRecord, status_code=status.HTTP_200_OK)
def get_verification(verification_id: str):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM verifications WHERE verification_id = ?", (verification_id,))
        row = cursor.fetchone()

    if not row:
        raise RoboWitnessException(
            status_code=404,
            code="VERIFICATION_NOT_FOUND",
            message=f"Verification {verification_id} does not exist"
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
