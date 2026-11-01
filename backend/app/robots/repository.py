"""Persistence and merging for the robot catalog (builtin seeds + user rows)."""

import uuid
from datetime import datetime, timezone

from app.db import get_db
from app.robots.catalog import builtin_robots
from app.schemas.robot_profile import RobotProfile, RobotProfileCreate, build_profile


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _key(brand: str, model: str, variant: str) -> tuple[str, str, str]:
    return (brand.strip().lower(), model.strip().lower(), variant.strip().lower())


def list_user_robots() -> list[RobotProfile]:
    with get_db() as conn:
        rows = conn.execute("SELECT profile_json FROM robots ORDER BY created_at ASC").fetchall()
    return [RobotProfile.model_validate_json(row["profile_json"]) for row in rows]


def list_robots() -> list[RobotProfile]:
    return builtin_robots() + list_user_robots()


def get_robot(robot_id: str) -> RobotProfile | None:
    for robot in list_robots():
        if robot.robot_id == robot_id:
            return robot
    return None


def find_duplicate(data: RobotProfileCreate, exclude_id: str | None = None) -> RobotProfile | None:
    wanted = _key(data.brand, data.model, data.variant)
    for robot in list_robots():
        if exclude_id is not None and robot.robot_id == exclude_id:
            continue
        if _key(robot.brand, robot.model, robot.variant) == wanted:
            return robot
    return None


def create_robot(data: RobotProfileCreate) -> RobotProfile:
    now = _now()
    profile = build_profile(data, f"robot-{uuid.uuid4().hex[:12]}", "user", now, now)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO robots (robot_id, profile_json, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (profile.robot_id, profile.model_dump_json(), now, now),
        )
        conn.commit()
    return profile


def update_robot(robot_id: str, data: RobotProfileCreate) -> RobotProfile | None:
    existing = get_robot(robot_id)
    if existing is None or existing.source != "user":
        return None
    profile = build_profile(data, robot_id, "user", existing.created_at, _now())
    with get_db() as conn:
        conn.execute(
            "UPDATE robots SET profile_json = ?, updated_at = ? WHERE robot_id = ?",
            (profile.model_dump_json(), profile.updated_at, robot_id),
        )
        conn.commit()
    return profile


def delete_robot(robot_id: str) -> bool:
    existing = get_robot(robot_id)
    if existing is None or existing.source != "user":
        return False
    with get_db() as conn:
        conn.execute("DELETE FROM robots WHERE robot_id = ?", (robot_id,))
        conn.commit()
    return True


def apply_profile_to_scenario(profile: RobotProfile, scenario):
    """Return a copy of ``scenario`` whose RobotSpec carries profile values.

    Start pose, goal and goal radius are scenario properties and are kept.
    Caller must check ``profile.simulation_compatible`` first.
    """
    robot = scenario.robot.model_copy(
        update={
            "body_radius_m": profile.body_radius_m,
            "wheel_base_m": profile.wheel_base_m
            if profile.wheel_base_m is not None
            else scenario.robot.wheel_base_m,
            "wheel_radius_m": profile.wheel_radius_m
            if profile.wheel_radius_m is not None
            else scenario.robot.wheel_radius_m,
            "sensor_range_m": profile.sensor_range_m,
            "sensor_latency_ms": profile.sensor_latency_ms,
            "sensor_noise_std_m": profile.sensor_noise_std_m,
        }
    )
    return scenario.model_copy(update={"robot": robot})


__all__ = [
    "list_robots",
    "get_robot",
    "find_duplicate",
    "create_robot",
    "update_robot",
    "delete_robot",
    "apply_profile_to_scenario",
]
