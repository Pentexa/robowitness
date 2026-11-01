"""Imported real-robot track schemas (measured elsewhere, judged here)."""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.scenario import Point2D


class ImportedFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    t_s: float
    x_m: float
    y_m: float
    yaw_rad: float = 0.0
    min_obstacle_distance_m: Optional[float] = None


class TelemetryImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Gerçek sürüş", max_length=120)
    robot_label: str = Field(default="", max_length=120)
    format: Literal["csv", "json"]
    content: str = Field(max_length=8_000_000)
    goal: Optional[Point2D] = None
    goal_radius_m: float = Field(default=0.35, ge=0.05, le=2.0)
    min_clearance_limit_m: float = Field(default=0.25, ge=0.0, le=2.0)


class ImportMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frame_count: int
    duration_s: float
    min_clearance_m: Optional[float] = None
    collision_detected: bool = False
    goal_reached: Optional[bool] = None
    final_goal_distance_m: Optional[float] = None
    path_length_m: float = 0.0


class TelemetryImportResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    import_id: str
    name: str
    robot_label: str = ""
    provenance: Literal["REAL_LOG"] = "REAL_LOG"
    oracle_status: Literal["PASS", "FAIL", "INCONCLUSIVE"]
    reason_codes: List[str] = Field(default_factory=list)
    near_miss: bool = False
    metrics: ImportMetrics
    created_at: str
