"""AI adapter protocols and model implementations."""
import json
from typing import Optional, Protocol
from app.config import settings
from app.schemas.ai import AIProvenance, InvestigationResponse
from app.schemas.policy import PolicyPatch
from app.schemas.scenario import ScenarioSpec

class ModelAdapter(Protocol):
    def generate_scenario(self, prompt: str) -> tuple[Optional[ScenarioSpec], AIProvenance]:
        ...

    def investigate_failure(self, failure_summary: str) -> tuple[Optional[InvestigationResponse], AIProvenance]:
        ...

class OfflineReferenceAdapter:
    def __init__(self, reference_spec_path=None):
        self.reference_spec_path = reference_spec_path

    def generate_scenario(self, prompt: str) -> tuple[Optional[ScenarioSpec], AIProvenance]:
        from app.schemas.scenario import ObstacleSpec, OracleSpec, Point2D, Pose2D, RobotSpec, ScenarioSpec, WorldSpec
        spec = ScenarioSpec(
            id="RW-AI-GEN-001",
            kind="dynamic_obstacle",
            seed=4242,
            world=WorldSpec(width_m=12.0, height_m=8.0, duration_limit_s=30.0),
            robot=RobotSpec(
                start=Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0),
                goal=Point2D(x_m=11.0, y_m=4.0),
                goal_radius_m=0.35,
                body_radius_m=0.25,
                sensor_latency_ms=450,
                sensor_noise_std_m=0.01,
            ),
            obstacles=[
                ObstacleSpec(
                    id="AI_O1",
                    shape="circle",
                    radius_m=0.35,
                    motion="ping_pong",
                    start=Point2D(x_m=6.0, y_m=1.2),
                    end=Point2D(x_m=6.0, y_m=6.8),
                    speed_mps=0.45,
                )
            ],
            oracle=OracleSpec(max_duration_s=30.0),
        )
        return spec, "OFFLINE_REFERENCE"

    def investigate_failure(self, failure_summary: str) -> tuple[Optional[InvestigationResponse], AIProvenance]:
        inv = InvestigationResponse(
            investigation_id="inv-offline-ref",
            run_id="run-ref",
            failure_tick=124,
            hypothesis="Observation latency of 450ms causes obstacle position to be reported late, delaying deceleration until overlap is unavoidable.",
            evidence_summary="At tick 124, clearance dropped below 0.0m while forward speed remained 0.75 m/s.",
            suggested_patch=PolicyPatch(
                max_speed_mps=0.45,
                safe_distance_m=0.85,
                reaction_margin_m=0.15,
                brake_gain=3.0,
                obstacle_prediction_horizon_s=0.60,
            ),
            provenance="OFFLINE_REFERENCE",
        )
        return inv, "OFFLINE_REFERENCE"

class MetaAdapter:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model

    def generate_scenario(self, prompt: str) -> tuple[Optional[ScenarioSpec], AIProvenance]:
        if not self.api_key:
            return None, "UNAVAILABLE"
        # Bounded external API call would be placed here
        return None, "UNAVAILABLE"

    def investigate_failure(self, failure_summary: str) -> tuple[Optional[InvestigationResponse], AIProvenance]:
        if not self.api_key:
            return None, "UNAVAILABLE"
        return None, "UNAVAILABLE"

def get_ai_adapter() -> ModelAdapter:
    if settings.RW_AI_MODE == "live" and settings.RW_META_API_KEY:
        return MetaAdapter(
            api_key=settings.RW_META_API_KEY,
            base_url=settings.RW_META_BASE_URL,
            model=settings.RW_META_MODEL,
        )
    return OfflineReferenceAdapter()
