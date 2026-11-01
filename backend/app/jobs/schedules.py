"""Due-schedule enqueuing: called by the worker loop on a throttle.

A schedule whose next_run_at has passed enqueues exactly one battery job and
advances next_run_at by its interval (no catch-up storm after downtime).
"""

import json
from datetime import datetime, timedelta, timezone

from app.db import get_db

_last_check = 0.0
CHECK_INTERVAL_S = 5.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def enqueue_due_schedules(force: bool = False) -> int:
    global _last_check
    import time

    now_t = time.time()
    if not force and (now_t - _last_check) < CHECK_INTERVAL_S:
        return 0
    _last_check = now_t

    from app.api.routes_batteries import _enqueue_battery
    from app.schemas.battery import BatteryRunRequest
    from app.schemas.policy import PolicyConfig

    now = _now()
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM battery_schedules WHERE enabled = 1 AND next_run_at <= ?",
            (now.isoformat(),),
        ).fetchall()

    enqueued = 0
    for row in rows:
        try:
            request = BatteryRunRequest(
                robot_id=row["robot_id"],
                scenario_ids=json.loads(row["scenario_ids_json"]),
                policy=PolicyConfig.model_validate_json(row["policy_json"]),
                local_policy=row["local_policy"],
            )
            _enqueue_battery(request, row["workspace_id"])
            next_run = now + timedelta(minutes=row["interval_minutes"])
            with get_db() as conn:
                conn.execute(
                    "UPDATE battery_schedules SET last_run_at = ?, next_run_at = ? "
                    "WHERE schedule_id = ?",
                    (now.isoformat(), next_run.isoformat(), row["schedule_id"]),
                )
                conn.commit()
            enqueued += 1
        except Exception as exc:
            print(f"[schedule] {row['schedule_id']} could not enqueue: {exc}")
    return enqueued
