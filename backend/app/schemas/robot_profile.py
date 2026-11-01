"""Robot catalog profile schemas.

A robot profile is catalog data (brand/model/features as entered by the user).
It is NOT physics truth: only the fields mapped into ``RobotSpec`` by
``apply_profile_to_scenario`` ever reach the simulator, and only when the
profile is simulation-compatible.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field

DriveType = Literal[
    "differential_drive", "ackermann", "omnidirectional", "tracked", "quadruped", "other"
]

# Simulator limits, mirroring RobotSpec in app/schemas/scenario.py.
SIM_BODY_RADIUS_MIN_M = 0.15
SIM_BODY_RADIUS_MAX_M = 0.40


class RobotProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brand: str = Field(min_length=1, max_length=60)
    model: str = Field(min_length=1, max_length=80)
    variant: str = Field(default="", max_length=60)
    year: Optional[int] = Field(default=None, ge=1990, le=2100)
    drive_type: DriveType = "differential_drive"
    body_radius_m: float = Field(ge=0.05, le=1.0)
    wheel_base_m: Optional[float] = Field(default=None, gt=0.0, le=2.0)
    wheel_radius_m: Optional[float] = Field(default=None, gt=0.0, le=1.0)
    weight_kg: Optional[float] = Field(default=None, gt=0.0, le=5000.0)
    max_speed_mps: Optional[float] = Field(default=None, ge=0.0, le=5.0)
    max_payload_kg: Optional[float] = Field(default=None, ge=0.0, le=5000.0)
    sensor_type: str = Field(default="2D LiDAR", min_length=1, max_length=60)
    sensor_range_m: float = Field(default=4.0, gt=0.0, le=30.0)
    sensor_latency_ms: int = Field(default=0, ge=0, le=1000)
    sensor_noise_std_m: float = Field(default=0.0, ge=0.0, le=0.2)
    compute_unit: str = Field(default="", max_length=120)
    operating_system: str = Field(default="", max_length=120)
    battery_wh: Optional[float] = Field(default=None, ge=0.0, le=100000.0)
    notes: str = Field(default="", max_length=1000)


def compatibility_issues(profile: RobotProfileCreate) -> List[str]:
    """Machine-readable reasons a profile cannot drive the simulator as-is."""
    issues: List[str] = []
    if profile.drive_type != "differential_drive":
        issues.append("DRIVE_TYPE_NOT_DIFFERENTIAL_DRIVE")
    if not (SIM_BODY_RADIUS_MIN_M <= profile.body_radius_m <= SIM_BODY_RADIUS_MAX_M):
        issues.append("BODY_RADIUS_OUT_OF_SIM_RANGE")
    return issues


class RobotProfile(RobotProfileCreate):
    robot_id: str
    source: Literal["builtin", "user"]
    created_at: str
    updated_at: str
    simulation_compatible: bool
    compatibility_issues: List[str] = Field(default_factory=list)


def build_profile(
    data: RobotProfileCreate, robot_id: str, source: str, created_at: str, updated_at: str
) -> RobotProfile:
    issues = compatibility_issues(data)
    return RobotProfile(
        **data.model_dump(),
        robot_id=robot_id,
        source=source,  # type: ignore[arg-type]
        created_at=created_at,
        updated_at=updated_at,
        simulation_compatible=len(issues) == 0,
        compatibility_issues=issues,
    )
