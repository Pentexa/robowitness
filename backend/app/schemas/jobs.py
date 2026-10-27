"""Durable Job schemas and status transitions."""
from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]
JobKind = Literal["simulation_run", "verification"]

class JobProgress(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pct: float = Field(default=0.0, ge=0.0, le=100.0)
    current_step: int = 0
    total_steps: int = 0
    message: str = ""

class JobRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str
    kind: JobKind
    status: JobStatus
    payload_json: str
    result_id: Optional[str] = None
    attempts: int = 0
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    lease_owner: Optional[str] = None
    lease_until: Optional[str] = None
    error_code: Optional[str] = None
    progress_json: Optional[str] = None

class JobResponse(BaseModel):
    job_id: str
    kind: JobKind
    status: JobStatus
    progress: Optional[JobProgress] = None
    result_id: Optional[str] = None
    error_code: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None

class JobCreateResponse(BaseModel):
    job_id: str
    result_id: str
    status: JobStatus = "queued"
