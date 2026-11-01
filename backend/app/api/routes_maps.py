"""Map import API: occupancy grid text -> validated scenario."""

from typing import List
from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict, Field
from app.errors import RoboWitnessException
from app.maps.converter import convert_grid_to_scenario
from app.schemas.scenario import ScenarioSpec

router = APIRouter(prefix="/maps", tags=["Maps"])


class MapConvertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(default="Haritam", max_length=120)
    grid_text: str = Field(max_length=200_000)
    cell_size_m: float = Field(default=0.5, gt=0.05, le=2.0)


class MapConvertResponse(BaseModel):
    scenario: ScenarioSpec
    warnings: List[str] = Field(default_factory=list)


@router.post("/scenario", response_model=MapConvertResponse, status_code=status.HTTP_200_OK)
def convert_map(request: MapConvertRequest):
    try:
        scenario, warnings = convert_grid_to_scenario(
            request.name, request.grid_text, request.cell_size_m
        )
    except Exception as exc:
        raise RoboWitnessException(status_code=422, code="MAP_CONVERSION_FAILED", message=str(exc))
    return MapConvertResponse(scenario=scenario, warnings=warnings)
