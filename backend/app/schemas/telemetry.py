"""AUTHORITATIVE Telemetry, Events, and Metrics schemas."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.scenario import Point2D, Pose2D

OracleStatus = Literal["PASS", "FAIL", "INCONCLUSIVE"]

class ObstacleTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    x_m: float
    y_m: float
    radius_m: float

class SensorTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sample_tick: int
    delivered_tick: int
    age_s: float
    valid: bool
    observations: List[Dict[str, Any]] = Field(default_factory=list)

class CommandTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    linear_mps: float
    angular_radps: float

class EventRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str
    type: str  # 'COLLISION', 'CLEARANCE_WARNING', 'GOAL_REACHED', 'STUCK', 'TIMEOUT'
    tick: int
    sim_time_s: float
    details: Dict[str, Any] = Field(default_factory=dict)

class TelemetryFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    tick: int
    sim_time_s: float
    robot: Pose2D
    obstacles: List[ObstacleTelemetry]
    sensor: SensorTelemetry
    command: CommandTelemetry
    clearance_m: float
    events: List[EventRecord] = Field(default_factory=list)

class RunMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_ticks: int
    sim_duration_s: float
    min_clearance_m: float
    goal_reached: bool
    collision_detected: bool
    stuck_detected: bool
    timeout_detected: bool

class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    scenario_id: str
    scenario_hash: str
    policy_hash: str
    job_status: str
    oracle_status: OracleStatus
    reason_codes: List[str] = Field(default_factory=list)
    metrics: RunMetrics
    artifact_path: str
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

class TelemetryPage(BaseModel):
    run_id: str
    frames: List[TelemetryFrame]
    total: int
    offset: int
    next_offset: Optional[int] = None
