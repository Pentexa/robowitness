"""Scenarios API routes."""
import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, status
from app.errors import RoboWitnessException
from app.schemas.ai import ScenarioGenerateRequest, ScenarioGenerateResponse
from app.schemas.scenario import ScenarioSpec

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])

def get_scenarios_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / "scenarios"

@router.get("/reference", response_model=List[ScenarioSpec], status_code=status.HTTP_200_OK)
def list_reference_scenarios():
    root = get_scenarios_root()
    ref_dir = root / "reference"
    results = []
    if ref_dir.exists():
        for f in ref_dir.glob("*.json"):
            try:
                with open(f, "r", encoding="utf-8") as spec_file:
                    data = json.load(spec_file)
                    results.append(ScenarioSpec.model_validate(data))
            except Exception as e:
                continue
    return results

@router.post("/generate", response_model=ScenarioGenerateResponse, status_code=status.HTTP_200_OK)
def generate_scenario(request: ScenarioGenerateRequest):
    # Offline fallback reference scenario
    root = get_scenarios_root()
    ref_file = root / "reference" / "moving_obstacle_latency.json"
    if not ref_file.exists():
        raise RoboWitnessException(
            status_code=404,
            code="SCENARIO_NOT_FOUND",
            message="Reference scenario file not found on disk"
        )
    with open(ref_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    spec = ScenarioSpec.model_validate(data)
    return ScenarioGenerateResponse(
        scenario=spec,
        provenance="OFFLINE_REFERENCE"
    )
