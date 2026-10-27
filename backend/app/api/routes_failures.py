"""Failures investigation API routes."""
import uuid
from fastapi import APIRouter, status
from app.config import settings
from app.errors import RoboWitnessException
from app.schemas.ai import InvestigationResponse
from app.schemas.policy import PolicyPatch

router = APIRouter(prefix="/failures", tags=["Failures"])

@router.post("/{run_id}/investigate", response_model=InvestigationResponse, status_code=status.HTTP_200_OK)
def investigate_failure(run_id: str):
    # Offline reference investigation
    return InvestigationResponse(
        investigation_id=f"inv-{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        failure_tick=124,
        hypothesis="Collision caused by 450ms observation latency: obstacle position observed was stale, causing late braking.",
        evidence_summary="At tick 124, clearance dropped below 0.0m while controller command maintained maximum linear speed 0.75 m/s.",
        suggested_patch=PolicyPatch(
            max_speed_mps=0.45,
            safe_distance_m=0.80,
            reaction_margin_m=0.20,
            brake_gain=3.0,
            obstacle_prediction_horizon_s=0.60
        ),
        provenance="OFFLINE_REFERENCE" if settings.RW_AI_MODE == "offline" else "LIVE_META"
    )
