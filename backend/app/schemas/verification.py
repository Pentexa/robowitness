"""Independent verification gate schemas and verdict contracts."""
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.policy import PolicyConfig

VerificationVerdict = Literal["VERIFIED_IN_SIMULATION", "REJECTED", "INCONCLUSIVE"]
GateStatus = Literal["PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN", "RUNNING"]

class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    gate_id: str
    name: str
    status: GateStatus
    reason_codes: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)

class HoldoutSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_cases: int = 20
    passed_cases: int = 0
    failed_cases: int = 0
    inconclusive_cases: int = 0
    details: List[Dict[str, Any]] = Field(default_factory=list)

class RegressionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")
    total_cases: int = 3
    passed_cases: int = 0
    failed_cases: int = 0
    details: List[Dict[str, Any]] = Field(default_factory=list)

class VerificationRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verification_id: str
    job_id: str
    baseline_run_id: str
    candidate_policy: PolicyConfig
    verdict: VerificationVerdict
    gates: List[GateResult] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    artifact_dir: str
    created_at: str
    completed_at: Optional[str] = None

class VerifyFixRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    baseline_run_id: str
    candidate_policy: PolicyConfig
