"""Battery schedule API: recurring exams per robot."""

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, ConfigDict, Field
from app.db import get_db
from app.errors import RoboWitnessException
from app.robots import repository as robots_repo
from app.schemas.policy import PolicyConfig
from app.security import current_workspace

router = APIRouter(prefix="/batteries/schedules", tags=["Battery Schedules"])


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=80)
    robot_id: str
    policy: PolicyConfig
    local_policy: Optional[str] = None
    scenario_ids: List[str] = Field(default_factory=list, max_length=30)
    interval_minutes: int = Field(ge=5, le=43_200)


class ScheduleView(BaseModel):
    schedule_id: str
    name: str
    robot_id: str
    interval_minutes: int
    next_run_at: str
    last_run_at: Optional[str] = None
    enabled: bool
    created_at: str


def _view(row) -> ScheduleView:
    return ScheduleView(
        schedule_id=row["schedule_id"],
        name=row["name"],
        robot_id=row["robot_id"],
        interval_minutes=row["interval_minutes"],
        next_run_at=row["next_run_at"],
        last_run_at=row["last_run_at"],
        enabled=bool(row["enabled"]),
        created_at=row["created_at"],
    )


@router.post("", response_model=ScheduleView, status_code=status.HTTP_201_CREATED)
def create_schedule(body: ScheduleCreate, request: Request):
    ws = current_workspace(request)
    robot = robots_repo.get_robot(body.robot_id, ws)
    if robot is None:
        raise RoboWitnessException(
            status_code=404, code="ROBOT_NOT_FOUND", message=f"Robot {body.robot_id} does not exist"
        )
    now = datetime.now(timezone.utc)
    schedule_id = f"schedule-{uuid.uuid4().hex[:12]}"
    next_run = (now + timedelta(minutes=body.interval_minutes)).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO battery_schedules (schedule_id, workspace_id, name, robot_id, "
            "policy_json, local_policy, scenario_ids_json, interval_minutes, next_run_at, "
            "enabled, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)",
            (
                schedule_id,
                ws,
                body.name,
                body.robot_id,
                body.policy.model_dump_json(),
                body.local_policy,
                json.dumps(body.scenario_ids),
                body.interval_minutes,
                next_run,
                now.isoformat(),
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM battery_schedules WHERE schedule_id = ?", (schedule_id,)
        ).fetchone()
    return _view(row)


@router.get("", response_model=List[ScheduleView], status_code=status.HTTP_200_OK)
def list_schedules(request: Request):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM battery_schedules WHERE workspace_id = ? ORDER BY created_at DESC",
            (current_workspace(request),),
        ).fetchall()
    return [_view(r) for r in rows]


@router.delete("/{schedule_id}", status_code=status.HTTP_200_OK)
def delete_schedule(schedule_id: str, request: Request):
    with get_db() as conn:
        cur = conn.execute(
            "DELETE FROM battery_schedules WHERE schedule_id = ? AND workspace_id = ?",
            (schedule_id, current_workspace(request)),
        )
        conn.commit()
    if cur.rowcount == 0:
        raise RoboWitnessException(
            status_code=404,
            code="SCHEDULE_NOT_FOUND",
            message=f"Schedule {schedule_id} does not exist",
        )
    return {"deleted": schedule_id}
