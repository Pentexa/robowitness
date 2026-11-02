"""Camera/photo -> real SAM detections -> preview/save ordinary ScenarioSpec."""

import hashlib
import os
from pathlib import Path
import tempfile
import uuid

from fastapi import APIRouter, Request

from app.ai.sam import SamAdapter, validate_image
from app.config import settings
from app.errors import RoboWitnessException
from app.maps.image_converter import image_to_scenario
from app.schemas.image_scenario import (
    ImageDetectRequest,
    ImageDetectionResult,
    ImageScenarioRequest,
    ImageScenarioResult,
)
from app.security import current_workspace

router = APIRouter(prefix="/scenarios/from-image", tags=["Scenarios"])


def _workspace_root(request: Request) -> Path:
    workspace = hashlib.sha256(current_workspace(request).encode()).hexdigest()
    return settings.artifacts_path / "image_scenarios" / workspace


def _write_json(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@router.post("/detect", response_model=ImageDetectionResult)
def detect_image(body: ImageDetectRequest, request: Request):
    width, height, digest = validate_image(body.image_data_url)
    detections = SamAdapter().detect(body.image_data_url, body.concepts, width, height)
    result = ImageDetectionResult(
        detection_id=f"img-{uuid.uuid4().hex[:24]}",
        image_width=width,
        image_height=height,
        image_sha256=digest,
        detections=detections,
    )
    # Keep measured detections and a source digest, not the user's photo.
    _write_json(
        _workspace_root(request) / "detections" / f"{result.detection_id}.json",
        result.model_dump_json(indent=2),
    )
    return result


@router.post("/scenario", response_model=ImageScenarioResult)
def preview_or_save_image_scenario(body: ImageScenarioRequest, request: Request):
    root = _workspace_root(request)
    path = root / "detections" / f"{body.detection_id}.json"
    if not path.is_file():
        raise RoboWitnessException(
            status_code=404,
            code="IMAGE_DETECTION_NOT_FOUND",
            message="Image detections were not found in this workspace",
        )
    detection = ImageDetectionResult.model_validate_json(path.read_text(encoding="utf-8"))
    try:
        scenario, notices = image_to_scenario(detection, body)
    except ValueError as exc:
        raise RoboWitnessException(
            status_code=422, code="IMAGE_SCENARIO_INVALID", message=str(exc)
        ) from exc
    result = ImageScenarioResult(
        scenario=scenario,
        name=body.name,
        detection_id=body.detection_id,
        saved=body.save,
        warnings=notices,
    )
    if body.save:
        _write_json(root / "saved" / f"{scenario.id}.json", result.model_dump_json(indent=2))
    return result


@router.get("/saved", response_model=list[ImageScenarioResult])
def list_saved_image_scenarios(request: Request):
    files = sorted(
        (_workspace_root(request) / "saved").glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return [
        ImageScenarioResult.model_validate_json(path.read_text(encoding="utf-8"))
        for path in files[:100]
    ]
