"""Policy configuration and controller contracts."""
import math
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

def check_finite(val: float, name: str) -> float:
    if not math.isfinite(val):
        raise ValueError(f"{name} must be a finite number")
    return val

class PolicyConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1.0"] = "1.0"
    id: str = Field(default="baseline-v1")
    max_speed_mps: float = Field(default=0.75, ge=0.05, le=1.2)
    safe_distance_m: float = Field(default=0.30, ge=0.20, le=2.0)
    reaction_margin_m: float = Field(default=0.05, ge=0.0, le=1.0)
    brake_gain: float = Field(default=1.5, ge=0.1, le=10.0)
    obstacle_prediction_horizon_s: float = Field(default=0.0, ge=0.0, le=2.0)

    @field_validator(
        "max_speed_mps",
        "safe_distance_m",
        "reaction_margin_m",
        "brake_gain",
        "obstacle_prediction_horizon_s",
    )
    @classmethod
    def validate_finite(cls, v: float, info) -> float:
        return check_finite(v, info.field_name)

class PolicyPatch(BaseModel):
    """Allowed patch fields from AI or user - strictly the 5 numeric parameters."""
    model_config = ConfigDict(extra="forbid")
    max_speed_mps: Optional[float] = Field(default=None, ge=0.05, le=1.2)
    safe_distance_m: Optional[float] = Field(default=None, ge=0.20, le=2.0)
    reaction_margin_m: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    brake_gain: Optional[float] = Field(default=None, ge=0.1, le=10.0)
    obstacle_prediction_horizon_s: Optional[float] = Field(default=None, ge=0.0, le=2.0)

class RelativeObstacleObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    rel_x_m: float
    rel_y_m: float
    radius_m: float
    distance_m: float

class SensorObservation(BaseModel):
    """Immutable sensor observation presented to controller."""
    model_config = ConfigDict(extra="forbid")
    sample_tick: int
    delivered_tick: int
    age_s: float
    valid: bool
    observed_pose: Optional[dict] = None
    goal_rel_x_m: float
    goal_rel_y_m: float
    goal_distance_m: float
    obstacles: List[RelativeObstacleObservation] = Field(default_factory=list)

class ControlCommand(BaseModel):
    model_config = ConfigDict(extra="forbid")
    linear_mps: float = Field(ge=-0.5, le=1.5)
    angular_radps: float = Field(ge=-math.pi, le=math.pi)

    @field_validator("linear_mps", "angular_radps")
    @classmethod
    def validate_finite(cls, v: float, info) -> float:
        return check_finite(v, info.field_name)
