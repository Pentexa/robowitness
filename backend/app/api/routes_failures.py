"""Failures investigation API routes — grounded in measured run telemetry."""

import json
import uuid
from pathlib import Path
from fastapi import APIRouter, status
from app.ai.adapter import OfflineReferenceAdapter, get_ai_adapter
from app.config import settings
from app.errors import RoboWitnessException
from app.schemas.ai import InvestigationResponse
from app.schemas.policy import PolicyPatch

router = APIRouter(prefix="/failures", tags=["Failures"])


def _run_dir(run_id: str) -> Path:
    base = (settings.artifacts_path / "runs").resolve()
    target = (base / run_id).resolve()
    if base not in target.parents and target != base:
        raise RoboWitnessException(status_code=403, code="FORBIDDEN_PATH", message="Access denied")
    if not target.is_dir():
        raise RoboWitnessException(
            status_code=404,
            code="RUN_NOT_FOUND",
            message=f"Run {run_id} has no recorded artifacts",
        )
    return target


def _measured_failure_evidence(run_dir: Path) -> dict:
    """Extract first COLLISION tick and minimum-clearance tick from recorded frames."""
    first_collision_tick = None
    min_clearance = float("inf")
    min_clearance_tick = None
    frames = 0
    with open(run_dir / "telemetry.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            frames += 1
            frame = json.loads(line)
            if frame.get("clearance_m", float("inf")) < min_clearance:
                min_clearance = frame["clearance_m"]
                min_clearance_tick = frame["tick"]
            for evt in frame.get("events", []):
                if evt.get("type") == "COLLISION" and first_collision_tick is None:
                    first_collision_tick = evt["tick"]
    metrics = {}
    metrics_file = run_dir / "metrics.json"
    if metrics_file.exists():
        metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    failure_tick = (
        first_collision_tick if first_collision_tick is not None else (min_clearance_tick or 0)
    )
    return {
        "failure_tick": failure_tick,
        "first_collision_tick": first_collision_tick,
        "min_clearance_m": min_clearance if min_clearance != float("inf") else None,
        "min_clearance_tick": min_clearance_tick,
        "total_frames": frames,
        "goal_reached": metrics.get("goal_reached"),
        "collision_detected": metrics.get("collision_detected"),
    }


@router.post(
    "/{run_id}/investigate",
    response_model=InvestigationResponse,
    status_code=status.HTTP_200_OK,
)
def investigate_failure(run_id: str):
    run_dir = _run_dir(run_id)
    try:
        ev = _measured_failure_evidence(run_dir)
    except FileNotFoundError:
        raise RoboWitnessException(
            status_code=404,
            code="TELEMETRY_NOT_FOUND",
            message=f"Telemetry for run {run_id} not found on disk",
        )

    parts = [f"Measured over {ev['total_frames']} recorded ticks."]
    if ev["first_collision_tick"] is not None:
        parts.append(f"First recorded contact at tick {ev['first_collision_tick']}.")
    if ev["min_clearance_m"] is not None:
        parts.append(
            f"Minimum surface clearance {ev['min_clearance_m']} m "
            f"at tick {ev['min_clearance_tick']}."
        )
    parts.append(f"Goal reached: {ev['goal_reached']}; collision: {ev['collision_detected']}.")
    evidence_summary = " ".join(parts)

    adapter = get_ai_adapter()
    if not isinstance(adapter, OfflineReferenceAdapter):
        inv, prov = adapter.investigate_failure(evidence_summary)
        if inv is not None:
            inv.run_id = run_id
            inv.failure_tick = ev["failure_tick"]
            return inv

    return InvestigationResponse(
        investigation_id=f"inv-{uuid.uuid4().hex[:12]}",
        run_id=run_id,
        failure_tick=ev["failure_tick"],
        hypothesis=(
            "Delayed sensor observations report stale obstacle positions, so braking "
            "starts late and the safety margin is consumed before the crossing completes."
        ),
        evidence_summary=evidence_summary,
        suggested_patch=PolicyPatch(
            max_speed_mps=0.45,
            safe_distance_m=0.80,
            reaction_margin_m=0.20,
            brake_gain=3.0,
            obstacle_prediction_horizon_s=0.60,
        ),
        provenance="OFFLINE_REFERENCE",
    )
