"""Sensor stress-test schemas: one scenario x (latency x noise) grid.

Every cell is a real, individually recorded simulation run judged by the
same oracle as any other run. The grid only varies the two sensor fields of
the scenario's robot spec; nothing about the oracle or gates changes.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.telemetry import OracleStatus, RunMetrics

MAX_LATENCIES = 8
MAX_NOISES = 6
MAX_CELLS = 40


class StressTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario: ScenarioSpec
    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    latencies_ms: List[int] = Field(min_length=1, max_length=MAX_LATENCIES)
    noise_levels_m: List[float] = Field(min_length=1, max_length=MAX_NOISES)


class StressCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latency_ms: int
    noise_std_m: float
    run_id: str
    oracle_status: OracleStatus
    reason_codes: List[str] = Field(default_factory=list)
    metrics: RunMetrics
    near_miss: bool = False


class StressSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total: int
    passed: int
    failed: int
    inconclusive: int
    near_misses: int
    worst_clearance_m: Optional[float] = None


class StressTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stress_id: str
    scenario_id: str
    policy_id: str
    latencies_ms: List[int] = Field(default_factory=list)
    noise_levels_m: List[float] = Field(default_factory=list)
    cells: List[StressCell] = Field(default_factory=list)
    summary: StressSummary
    created_at: str
    completed_at: Optional[str] = None


def summarize_cells(cells: List[StressCell]) -> StressSummary:
    return StressSummary(
        total=len(cells),
        passed=sum(1 for c in cells if c.oracle_status == "PASS"),
        failed=sum(1 for c in cells if c.oracle_status == "FAIL"),
        inconclusive=sum(1 for c in cells if c.oracle_status == "INCONCLUSIVE"),
        near_misses=sum(1 for c in cells if c.near_miss),
        worst_clearance_m=min((c.metrics.min_clearance_m for c in cells), default=None),
    )
