"""Battery (exam) API: run many scenarios for one robot, get a report card."""

import json
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Query, Request, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field
from app.api.routes_runs import validate_local_policy
from app.api.routes_scenarios import list_library_scenarios, list_reference_scenarios
from app.db import get_db
from app.errors import RoboWitnessException
from app.evidence.battery_report import generate_battery_report
from app.idempotency import get_idempotent_response, store_idempotent_response
from app.robots import repository as robots_repo
from app.schemas.battery import BatteryResult, BatteryRunRequest
from app.schemas.jobs import JobCreateResponse
from app.schemas.policy import PolicyConfig
from app.security import current_workspace

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


def _enqueue_battery(body: BatteryRunRequest, ws: str) -> JobCreateResponse:
    validate_local_policy(body.local_policy)
    robot = robots_repo.get_robot(body.robot_id, ws)
    if robot is None:
        raise RoboWitnessException(
            status_code=404,
            code="ROBOT_NOT_FOUND",
            message=f"Robot {body.robot_id} does not exist",
        )
    if not robot.simulation_compatible:
        raise RoboWitnessException(
            status_code=422,
            code="ROBOT_NOT_SIM_COMPATIBLE",
            message=("This robot cannot run the battery: " + ", ".join(robot.compatibility_issues)),
        )

    catalog = _catalog()
    scenario_ids = body.scenario_ids or default_battery_ids()
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
            "policy": body.policy.model_dump(),
            "local_policy": body.local_policy,
            "workspace_id": ws,
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


@router.post("", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED)
def create_battery(body: BatteryRunRequest, request: Request):
    existing = get_idempotent_response(request)
    if existing is not None:
        return existing
    response = _enqueue_battery(body, current_workspace(request))
    store_idempotent_response(request, response)
    return response


class FleetRunRequest(BaseModel):
    model_config = {"extra": "forbid"}

    robot_ids: List[str] = Field(min_length=1, max_length=20)
    scenario_ids: List[str] = Field(default_factory=list, max_length=30)
    policy: PolicyConfig
    local_policy: str | None = None


class FleetRunResponse(BaseModel):
    jobs: List[dict] = Field(default_factory=list)
    skipped: List[dict] = Field(default_factory=list)


@router.post("/fleet", response_model=FleetRunResponse, status_code=status.HTTP_202_ACCEPTED)
def create_fleet(body: FleetRunRequest, request: Request):
    """Enqueue one battery per robot; incompatible/unknown robots are skipped
    with a reason instead of failing the whole fleet request."""
    ws = current_workspace(request)
    policy = body.policy
    jobs: list[dict] = []
    skipped: list[dict] = []
    for robot_id in body.robot_ids:
        robot = robots_repo.get_robot(robot_id, ws)
        if robot is None:
            skipped.append({"robot_id": robot_id, "reason": "ROBOT_NOT_FOUND"})
            continue
        if not robot.simulation_compatible:
            skipped.append(
                {
                    "robot_id": robot_id,
                    "reason": "ROBOT_NOT_SIM_COMPATIBLE: " + ", ".join(robot.compatibility_issues),
                }
            )
            continue
        created = _enqueue_battery(
            BatteryRunRequest(
                robot_id=robot_id,
                scenario_ids=body.scenario_ids,
                policy=policy,
                local_policy=body.local_policy,
            ),
            ws,
        )
        jobs.append(
            {"robot_id": robot_id, "job_id": created.job_id, "battery_id": created.result_id}
        )
    return FleetRunResponse(jobs=jobs, skipped=skipped)


@router.get("", response_model=List[BatteryResult], status_code=status.HTTP_200_OK)
def list_batteries(request: Request, limit: int = Query(10, ge=1, le=50)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT result_json FROM battery_runs WHERE workspace_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (current_workspace(request), limit),
        ).fetchall()
    return [BatteryResult.model_validate_json(r["result_json"]) for r in rows]


def _load_battery(battery_id: str, workspace: str) -> BatteryResult:
    with get_db() as conn:
        row = conn.execute(
            "SELECT result_json FROM battery_runs WHERE battery_id = ? AND workspace_id = ?",
            (battery_id, workspace),
        ).fetchone()
    if row is None:
        raise RoboWitnessException(
            status_code=404,
            code="BATTERY_NOT_FOUND",
            message=f"Battery {battery_id} does not exist (not run yet?)",
        )
    return BatteryResult.model_validate_json(row["result_json"])


class BatteryTrendPoint(BaseModel):
    battery_id: str
    robot_id: str
    robot_label: str
    created_at: str
    passed: int
    total: int
    pass_rate: float
    collisions: int
    near_misses: int


@router.get("/trend", response_model=List[BatteryTrendPoint], status_code=status.HTTP_200_OK)
def battery_trend(
    request: Request,
    robot_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    """Pass-rate history over time (oldest first) for trend views."""
    with get_db() as conn:
        if robot_id:
            rows = conn.execute(
                "SELECT result_json FROM battery_runs WHERE workspace_id = ? AND robot_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (current_workspace(request), robot_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT result_json FROM battery_runs WHERE workspace_id = ? "
                "ORDER BY created_at DESC LIMIT ?",
                (current_workspace(request), limit),
            ).fetchall()
    points = []
    for row in reversed(rows):  # oldest first for charts
        card = BatteryResult.model_validate_json(row["result_json"])
        s = card.summary
        points.append(
            BatteryTrendPoint(
                battery_id=card.battery_id,
                robot_id=card.robot_id,
                robot_label=card.robot_label,
                created_at=card.created_at,
                passed=s.passed,
                total=s.total,
                pass_rate=round(s.passed / s.total, 4) if s.total else 0.0,
                collisions=s.collisions,
                near_misses=s.near_misses,
            )
        )
    return points


class BatteryCompareEntry(BaseModel):
    scenario_id: str
    title: str = ""
    status_a: str | None = None
    status_b: str | None = None
    clearance_a: float | None = None
    clearance_b: float | None = None
    outcome: str  # improved | worsened | same | only_a | only_b


class BatteryCompareResult(BaseModel):
    a: BatteryResult
    b: BatteryResult
    entries: List[BatteryCompareEntry] = Field(default_factory=list)
    summary_delta: dict = Field(default_factory=dict)


def _rank(status_: str | None) -> int:
    return {"PASS": 2, "INCONCLUSIVE": 1, "FAIL": 0}.get(status_ or "", -1)


@router.get("/compare", response_model=BatteryCompareResult, status_code=status.HTTP_200_OK)
def compare_batteries(request: Request, a: str = Query(...), b: str = Query(...)):
    ws = current_workspace(request)
    card_a = _load_battery(a, ws)
    card_b = _load_battery(b, ws)
    by_a = {e.scenario_id: e for e in card_a.entries}
    by_b = {e.scenario_id: e for e in card_b.entries}
    entries = []
    for sid in sorted(set(by_a) | set(by_b)):
        ea, eb = by_a.get(sid), by_b.get(sid)
        if ea is None:
            outcome = "only_b"
        elif eb is None:
            outcome = "only_a"
        elif _rank(eb.oracle_status) > _rank(ea.oracle_status):
            outcome = "improved"
        elif _rank(eb.oracle_status) < _rank(ea.oracle_status):
            outcome = "worsened"
        else:
            outcome = "same"
        entries.append(
            BatteryCompareEntry(
                scenario_id=sid,
                title=(eb or ea).title,
                status_a=ea.oracle_status if ea else None,
                status_b=eb.oracle_status if eb else None,
                clearance_a=ea.metrics.min_clearance_m if ea else None,
                clearance_b=eb.metrics.min_clearance_m if eb else None,
                outcome=outcome,
            )
        )
    return BatteryCompareResult(
        a=card_a,
        b=card_b,
        entries=entries,
        summary_delta={
            "passed_delta": card_b.summary.passed - card_a.summary.passed,
            "collisions_delta": card_b.summary.collisions - card_a.summary.collisions,
            "near_misses_delta": card_b.summary.near_misses - card_a.summary.near_misses,
        },
    )


@router.get("/{battery_id}", response_model=BatteryResult, status_code=status.HTTP_200_OK)
def get_battery(battery_id: str, request: Request):
    return _load_battery(battery_id, current_workspace(request))


@router.get("/{battery_id}/report.md", status_code=status.HTTP_200_OK)
def download_battery_report(
    battery_id: str, request: Request, lang: str = Query("tr")
):
    report = generate_battery_report(
        _load_battery(battery_id, current_workspace(request)), lang=lang
    )
    return PlainTextResponse(
        content=report,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{battery_id}-karne.md"'},
    )
