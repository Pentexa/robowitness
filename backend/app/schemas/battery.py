"""Battery (exam) schemas: one robot x many scenarios -> one report card."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.policy import PolicyConfig
from app.schemas.telemetry import OracleStatus, RunMetrics


class BatteryRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    robot_id: str
    scenario_ids: List[str] = Field(default_factory=list, max_length=30)
    policy: PolicyConfig
    local_policy: Optional[str] = None


class BatteryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str
    title: str = ""
    run_id: str
    oracle_status: OracleStatus
    reason_codes: List[str] = Field(default_factory=list)
    metrics: RunMetrics
    near_miss: bool = False


class BatterySummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    passed: int
    failed: int
    inconclusive: int
    collisions: int
    near_misses: int
    worst_clearance_m: Optional[float] = None


class BatteryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    battery_id: str
    robot_id: str
    robot_label: str
    policy_id: str
    entries: List[BatteryEntry] = Field(default_factory=list)
    summary: BatterySummary
    created_at: str
    completed_at: Optional[str] = None


def is_near_miss(status: str, reasons: List[str], metrics: RunMetrics) -> bool:
    """Single source of truth, mirrored by the UI: goal reached, no crash,
    but the safety clearance was violated."""
    return (
        status == "FAIL"
        and not metrics.collision_detected
        and metrics.goal_reached
        and "MIN_CLEARANCE_VIOLATION" in reasons
    )


def summarize(entries: List[BatteryEntry]) -> BatterySummary:
    return BatterySummary(
        total=len(entries),
        passed=sum(1 for e in entries if e.oracle_status == "PASS"),
        failed=sum(1 for e in entries if e.oracle_status == "FAIL"),
        inconclusive=sum(1 for e in entries if e.oracle_status == "INCONCLUSIVE"),
        collisions=sum(1 for e in entries if e.metrics.collision_detected),
        near_misses=sum(1 for e in entries if e.near_miss),
        worst_clearance_m=min((e.metrics.min_clearance_m for e in entries), default=None),
    )
