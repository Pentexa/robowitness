"""Canonical Scenario specification and geometry schemas."""

import math
from typing import List, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def check_finite(val: float, name: str) -> float:
    if not math.isfinite(val):
        raise ValueError(f"{name} must be a finite number")
    return val


def normalize_angle(rad: float) -> float:
    check_finite(rad, "yaw_rad")
    return (rad + math.pi) % (2.0 * math.pi) - math.pi


class Point2D(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x_m: float
    y_m: float

    @field_validator("x_m", "y_m")
    @classmethod
    def validate_finite(cls, v: float, info) -> float:
        return check_finite(v, info.field_name)


class Pose2D(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x_m: float
    y_m: float
    yaw_rad: float

    @field_validator("x_m", "y_m")
    @classmethod
    def validate_pos(cls, v: float, info) -> float:
        return check_finite(v, info.field_name)

    @field_validator("yaw_rad")
    @classmethod
    def validate_yaw(cls, v: float) -> float:
        return normalize_angle(v)


class Vector2D(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x_mps: float
    y_mps: float

    @field_validator("x_mps", "y_mps")
    @classmethod
    def validate_finite(cls, v: float, info) -> float:
        return check_finite(v, info.field_name)


class WorldSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["warehouse"] = "warehouse"
    width_m: float = Field(ge=6.0, le=20.0)
    height_m: float = Field(ge=4.0, le=15.0)
    duration_limit_s: float = Field(ge=5.0, le=60.0)
    fixed_timestep_s: float = Field(default=1.0 / 60.0)

    @field_validator("width_m", "height_m", "duration_limit_s", "fixed_timestep_s")
    @classmethod
    def validate_finite(cls, v: float, info) -> float:
        return check_finite(v, info.field_name)


class RobotSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["differential_drive"] = "differential_drive"
    start: Pose2D
    goal: Point2D
    goal_radius_m: float = Field(ge=0.20, le=0.60)
    body_radius_m: float = Field(ge=0.15, le=0.40)
    wheel_base_m: float = Field(default=0.42, gt=0.0)
    wheel_radius_m: float = Field(default=0.09, gt=0.0)
    sensor_range_m: float = Field(default=4.0, gt=0.0)
    sensor_latency_ms: int = Field(ge=0, le=1000)
    sensor_noise_std_m: float = Field(ge=0.0, le=0.2)


class ObstacleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    shape: Literal["circle"] = "circle"
    radius_m: float = Field(ge=0.15, le=0.80)
    motion: Literal["static", "ping_pong"]
    start: Point2D
    end: Point2D
    speed_mps: float = Field(ge=0.0, le=1.5)

    @model_validator(mode="after")
    def validate_motion(self) -> "ObstacleSpec":
        if self.motion == "static":
            if self.speed_mps != 0.0:
                raise ValueError("Static obstacle must have speed_mps == 0.0")
        elif self.motion == "ping_pong":
            if self.speed_mps <= 0.0:
                raise ValueError("Moving ping-pong obstacle must have positive speed_mps")
        return self


class OracleSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    collision_free: bool = True
    min_clearance_m: float = Field(default=0.25, ge=0.0, le=1.0)
    must_reach_goal: bool = True
    max_duration_s: float = Field(ge=5.0, le=60.0)
    max_stuck_duration_s: float = Field(default=3.0, ge=0.5, le=10.0)


class ScenarioSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    id: str
    kind: Literal["static_obstacle", "dynamic_obstacle"]
    seed: int = Field(ge=0, le=4294967295)
    world: WorldSpec
    robot: RobotSpec
    obstacles: List[ObstacleSpec] = Field(default_factory=list, max_length=8)
    oracle: OracleSpec

    @model_validator(mode="after")
    def validate_scenario(self) -> "ScenarioSpec":
        w = self.world.width_m
        h = self.world.height_m
        r_rad = self.robot.body_radius_m

        # 1. Robot start inside warehouse with margin
        if not (
            r_rad <= self.robot.start.x_m <= w - r_rad
            and r_rad <= self.robot.start.y_m <= h - r_rad
        ):
            raise ValueError(
                f"Robot start ({self.robot.start.x_m}, {self.robot.start.y_m}) "
                f"out of bounds for radius {r_rad}"
            )

        # 2. Robot goal inside warehouse with margin
        g_rad = self.robot.goal_radius_m
        if not (
            g_rad <= self.robot.goal.x_m <= w - g_rad and g_rad <= self.robot.goal.y_m <= h - g_rad
        ):
            raise ValueError(
                f"Robot goal ({self.robot.goal.x_m}, {self.robot.goal.y_m}) out of bounds"
            )

        # 3. Obstacle IDs unique and motion inside bounds
        seen_ids = set()
        for obs in self.obstacles:
            if obs.id in seen_ids:
                raise ValueError(f"Duplicate obstacle ID: {obs.id}")
            seen_ids.add(obs.id)

            o_rad = obs.radius_m
            for pt_name, pt in [("start", obs.start), ("end", obs.end)]:
                if not (o_rad <= pt.x_m <= w - o_rad and o_rad <= pt.y_m <= h - o_rad):
                    raise ValueError(
                        f"Obstacle {obs.id} {pt_name} position out of warehouse bounds"
                    )

            # 4. Check initial overlap with robot
            dist_to_robot = math.hypot(
                obs.start.x_m - self.robot.start.x_m,
                obs.start.y_m - self.robot.start.y_m,
            )
            if dist_to_robot < (r_rad + o_rad):
                raise ValueError(f"Obstacle {obs.id} overlaps with robot at start position")

        # 5. Check obstacle-to-obstacle initial overlap
        for i in range(len(self.obstacles)):
            for j in range(i + 1, len(self.obstacles)):
                o1 = self.obstacles[i]
                o2 = self.obstacles[j]
                d = math.hypot(o1.start.x_m - o2.start.x_m, o1.start.y_m - o2.start.y_m)
                if d < (o1.radius_m + o2.radius_m):
                    raise ValueError(f"Initial overlap between obstacles {o1.id} and {o2.id}")

        # 6. Oracle max_duration_s <= world duration_limit_s
        if self.oracle.max_duration_s > self.world.duration_limit_s:
            raise ValueError(
                f"Oracle max_duration_s ({self.oracle.max_duration_s}) cannot exceed "
                f"world duration_limit_s ({self.world.duration_limit_s})"
            )

        return self
