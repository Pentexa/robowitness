"""AI integration schemas, provenance tags, and bounded proposal models."""
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.policy import PolicyPatch
from app.schemas.scenario import ScenarioSpec

AIProvenance = Literal["LIVE_META", "OFFLINE_REFERENCE", "UNAVAILABLE"]

class ScenarioGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    objective: Optional[str] = Field(default=None, max_length=500)
    constraints: Optional[Dict[str, Any]] = None

class ScenarioGenerateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario: ScenarioSpec
    provenance: AIProvenance

class InvestigationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    investigation_id: str
    run_id: str
    failure_tick: int
    hypothesis: str
    evidence_summary: str
    suggested_patch: PolicyPatch
    provenance: AIProvenance
