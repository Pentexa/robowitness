"""Scenarios API routes."""

import json
from pathlib import Path
from typing import List
from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from app.ai.adapter import OfflineReferenceAdapter, get_ai_adapter
from app.errors import RoboWitnessException
from app.schemas.ai import ScenarioGenerateRequest, ScenarioGenerateResponse
from app.schemas.scenario import ScenarioSpec

router = APIRouter(prefix="/scenarios", tags=["Scenarios"])


class ScenarioCatalogEntry(BaseModel):
    scenario: ScenarioSpec
    title: str
    description: str = ""
    difficulty: str = ""
    category: str = ""
    tags: List[str] = Field(default_factory=list)


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
            except Exception:
                continue
    return results


def _load_catalog_dir(directory: Path) -> List[ScenarioCatalogEntry]:
    catalog_file = directory / "catalog.json"
    if not catalog_file.exists():
        return []
    with open(catalog_file, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    results = []
    for entry in catalog.get("entries", []):
        spec_file = directory / entry["file"]
        if not spec_file.exists():
            continue
        try:
            with open(spec_file, "r", encoding="utf-8") as spec_f:
                spec = ScenarioSpec.model_validate(json.load(spec_f))
        except Exception:
            continue
        results.append(
            ScenarioCatalogEntry(
                scenario=spec,
                title=entry.get("title", spec.id),
                description=entry.get("description", ""),
                difficulty=entry.get("difficulty", ""),
                category=entry.get("category", ""),
                tags=entry.get("tags", []),
            )
        )
    return results


@router.get("/library", response_model=List[ScenarioCatalogEntry], status_code=status.HTTP_200_OK)
def list_library_scenarios():
    root = get_scenarios_root()
    return (
        _load_catalog_dir(root / "library")
        + _load_catalog_dir(root / "ultra")
        + _load_catalog_dir(root / "crowd")
    )


@router.post("/generate", response_model=ScenarioGenerateResponse, status_code=status.HTTP_200_OK)
def generate_scenario(request: ScenarioGenerateRequest):
    adapter = get_ai_adapter()

    if isinstance(adapter, OfflineReferenceAdapter):
        return _offline_reference_scenario()

    spec, provenance = adapter.generate_scenario(request.objective or "")
    if spec is not None:
        return ScenarioGenerateResponse(scenario=spec, provenance=provenance)
    raise RoboWitnessException(
        status_code=503,
        code="META_PROVIDER_UNAVAILABLE",
        message="Live Meta provider call failed validation or transport; no scenario generated",
    )


def _offline_reference_scenario() -> ScenarioGenerateResponse:
    root = get_scenarios_root()
    ref_file = root / "reference" / "moving_obstacle_latency.json"
    if not ref_file.exists():
        raise RoboWitnessException(
            status_code=404,
            code="SCENARIO_NOT_FOUND",
            message="Reference scenario file not found on disk",
        )
    with open(ref_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    spec = ScenarioSpec.model_validate(data)
    return ScenarioGenerateResponse(scenario=spec, provenance="OFFLINE_REFERENCE")
