"""Adversarial testing schemas: bounded AI scenario generation, oracle-judged."""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.ai import AIProvenance
from app.schemas.policy import PolicyConfig
from app.schemas.telemetry import OracleStatus


class AdversarialTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy: PolicyConfig = Field(default_factory=PolicyConfig)
    max_iterations: Optional[int] = Field(default=None, ge=1, le=10)
    seed_run_id: Optional[str] = None


class AdversarialRound(BaseModel):
    model_config = ConfigDict(extra="forbid")

    iteration: int
    scenario_id: Optional[str] = None
    provenance: AIProvenance
    executed: bool
    run_id: Optional[str] = None
    oracle_status: Optional[OracleStatus] = None
    reason_codes: List[str] = Field(default_factory=list)
    min_clearance_m: Optional[float] = None
    note: str = ""


class AdversarialResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adversarial_id: str
    policy_id: str
    max_iterations: int
    rounds: List[AdversarialRound] = Field(default_factory=list)
    executed_count: int = 0
    fail_count: int = 0
    pass_count: int = 0
    total_tokens_used: int = 0
    stopped_reason: str = "iteration_limit"
    created_at: str
    completed_at: Optional[str] = None
