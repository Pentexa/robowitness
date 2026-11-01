"""Real-robot telemetry import API: upload a measured track, get it judged."""

import csv
import io
import json
import uuid
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Query, Request, status
from app.db import get_db
from app.errors import RoboWitnessException
from app.security import current_workspace
from app.schemas.telemetry_import import (
    ImportedFrame,
    TelemetryImportRequest,
    TelemetryImportResult,
)
from app.verification.log_oracle import evaluate_imported_track

router = APIRouter(prefix="/imports", tags=["Telemetry Imports"])

_NUMERIC_FIELDS = ("t_s", "x_m", "y_m", "yaw_rad", "min_obstacle_distance_m")


def _parse_csv(content: str) -> List[ImportedFrame]:
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames is None or "t_s" not in reader.fieldnames:
        raise ValueError("CSV must have a header row including t_s, x_m, y_m")
    frames = []
    for row in reader:
        data = {}
        for field in _NUMERIC_FIELDS:
            raw = (row.get(field) or "").strip()
            if raw == "":
                continue
            data[field] = float(raw)
        frames.append(ImportedFrame.model_validate(data))
    return frames


def _parse_json(content: str) -> List[ImportedFrame]:
    data = json.loads(content)
    if isinstance(data, dict):
        data = data.get("frames", [])
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of frames or an object with 'frames'")
    return [ImportedFrame.model_validate(item) for item in data]


def _bad_import(reason: str) -> RoboWitnessException:
    return RoboWitnessException(status_code=422, code="IMPORT_PARSE_ERROR", message=reason)


@router.post(
    "/telemetry", response_model=TelemetryImportResult, status_code=status.HTTP_201_CREATED
)
def import_telemetry(body: TelemetryImportRequest, request: Request):
    try:
        frames = _parse_csv(body.content) if body.format == "csv" else _parse_json(body.content)
    except Exception as exc:
        raise _bad_import(f"Could not parse {body.format} telemetry: {exc}")

    if not frames:
        raise _bad_import("No telemetry frames found in the uploaded content")

    try:
        oracle_status, reasons, metrics = evaluate_imported_track(
            frames,
            goal=body.goal,
            goal_radius_m=body.goal_radius_m,
            min_clearance_limit_m=body.min_clearance_limit_m,
        )
    except ValueError as exc:
        raise _bad_import(str(exc))

    near_miss = (
        oracle_status == "FAIL"
        and not metrics.collision_detected
        and metrics.goal_reached is True
        and "MIN_CLEARANCE_VIOLATION" in reasons
    )

    result = TelemetryImportResult(
        import_id=f"import-{uuid.uuid4().hex[:12]}",
        name=body.name,
        robot_label=body.robot_label,
        oracle_status=oracle_status,  # type: ignore[arg-type]
        reason_codes=reasons,
        near_miss=near_miss,
        metrics=metrics,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    with get_db() as conn:
        conn.execute(
            "INSERT INTO telemetry_imports (import_id, result_json, created_at, workspace_id) "
            "VALUES (?, ?, ?, ?)",
            (
                result.import_id,
                result.model_dump_json(),
                result.created_at,
                current_workspace(request),
            ),
        )
        conn.commit()
    return result


@router.get("", response_model=List[TelemetryImportResult], status_code=status.HTTP_200_OK)
def list_imports(request: Request, limit: int = Query(10, ge=1, le=50)):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT result_json FROM telemetry_imports WHERE workspace_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (current_workspace(request), limit),
        ).fetchall()
    return [TelemetryImportResult.model_validate_json(r["result_json"]) for r in rows]


@router.get("/{import_id}", response_model=TelemetryImportResult, status_code=status.HTTP_200_OK)
def get_import(import_id: str, request: Request):
    with get_db() as conn:
        row = conn.execute(
            "SELECT result_json FROM telemetry_imports WHERE import_id = ? AND workspace_id = ?",
            (import_id, current_workspace(request)),
        ).fetchone()
    if row is None:
        raise RoboWitnessException(
            status_code=404, code="IMPORT_NOT_FOUND", message=f"Import {import_id} does not exist"
        )
    return TelemetryImportResult.model_validate_json(row["result_json"])
