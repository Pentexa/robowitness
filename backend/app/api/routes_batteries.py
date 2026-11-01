"""Battery (exam) API: run many scenarios for one robot, get a report card."""

import json
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Query, status
from fastapi.responses import PlainTextResponse
from app.api.routes_runs import validate_local_policy
from app.api.routes_scenarios import list_library_scenarios, list_reference_scenarios
from app.db import get_db
from app.errors import RoboWitnessException
from app.evidence.battery_report import generate_battery_report
from app.robots import repository as robots_repo
from app.schemas.battery import BatteryResult, BatteryRunRequest
from app.schemas.jobs import JobCreateResponse

router = APIRouter(prefix="/batteries", tags=["Batteries"])


def _catalog() -> dict[str, tuple[object, str]]:
    """scenario_id -> (ScenarioSpec, title) for everything a battery may run."""
    catalog: dict[str, tuple[object, str]] = {}
    for entry in list_library_scenarios():
        catalog[entry.scenario.id] = (entry.scenario, entry.title)
    for spec in list_reference_scenarios():
        catalog.setdefault(spec.id, (spec, "Hazır Test (Referans)"))
    return catalog


def default_battery_ids() -> list[str]:
    catalog = _catalog()
    ids = []
    if "RW-REF-001" in catalog:
        ids.append("RW-REF-001")
    ids.extend(sid for sid in catalog if sid.startswith("RW-LIB-"))
    return ids


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_battery(request: BatteryRunRequest):
    validate_local_policy(request.local_policy)
    robot = robots_repo.get_robot(request.robot_id)
    if robot is None:
        raise RoboWitnessException(
            status_code=404,
            code="ROBOT_NOT_FOUND",
            message=f"Robot {request.robot_id} does not exist",
        )
    if not robot.simulation_compatible:
        raise RoboWitnessException(
            status_code=422,
            code="ROBOT_NOT_SIM_COMPATIBLE",
            message=("This robot cannot run the battery: " + ", ".join(robot.compatibility_issues)),
        )

    catalog = _catalog()
    scenario_ids = request.scenario_ids or default_battery_ids()
    unknown = [sid for sid in scenario_ids if sid not in catalog]
    if unknown:
        raise RoboWitnessException(
            status_code=422,
            code="SCENARIO_NOT_IN_BATTERY_CATALOG",
            message=f"Unknown scenario ids for battery: {', '.join(unknown)}",
        )

    items = []
    for sid in scenario_ids:
        spec, title = catalog[sid]
        applied = robots_repo.apply_profile_to_scenario(robot, spec)
        items.append({"scenario": applied.model_dump(), "title": title})

    job_id = f"job-{uuid.uuid4().hex[:12]}"
    battery_id = f"battery-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(
        {
            "robot_id": robot.robot_id,
            "robot_label": f"{robot.brand} {robot.model}",
            "policy": request.policy.model_dump(),
            "local_policy": request.local_policy,
            "scenarios": items,
        }
    )
    with get_db() as conn:
        conn.execute(
            "INSERT INTO jobs (job_id, kind, status, payload_json, result_id, "
            "attempts, created_at) VALUES (?, 'battery_run', 'queued', ?, ?, 0, ?)",
            (job_id, payload, battery_id, now),
        )
        conn.commit()
    return JobCreateResponse(job_id=job_id, result_id=battery_id, status="queued")


@router.get("", response_model=List[BatteryResult], status_code=status.HTTP_200_OK)
def list_batteries(limit: int = Query(10, ge=1, le=50)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT result_json FROM battery_runs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [BatteryResult.model_validate_json(r["result_json"]) for r in rows]


@router.get("/{battery_id}", response_model=BatteryResult, status_code=status.HTTP_200_OK)
def get_battery(battery_id: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT result_json FROM battery_runs WHERE battery_id = ?", (battery_id,)
        ).fetchone()
    if row is None:
        raise RoboWitnessException(
            status_code=404,
            code="BATTERY_NOT_FOUND",
            message=f"Battery {battery_id} does not exist (not run yet?)",
        )
    return BatteryResult.model_validate_json(row["result_json"])


@router.get("/{battery_id}/report.md", status_code=status.HTTP_200_OK)
def download_battery_report(battery_id: str):
    report = generate_battery_report(get_battery(battery_id))
    return PlainTextResponse(
        content=report,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{battery_id}-karne.md"'},
    )
