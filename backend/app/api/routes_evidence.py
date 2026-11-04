"""Evidence package inspection and safe download routes."""

import base64
import binascii
import io
import json
import zipfile
from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse
from app.config import settings
from app.errors import RoboWitnessException
from app.evidence.inspector import (
    EvidenceInspectReport,
    EvidenceInspectRequest,
    inspect_evidence_zip,
)

router = APIRouter(prefix="/evidence", tags=["Evidence"])


@router.post("/inspect", response_model=EvidenceInspectReport, status_code=status.HTTP_200_OK)
def inspect_uploaded_evidence(body: EvidenceInspectRequest):
    """Independently verify an uploaded evidence ZIP (base64, JSON API style).

    Placed before the /{verification_id} route so 'inspect' is not parsed
    as a verification id.
    """
    try:
        data = base64.b64decode(body.content_base64, validate=True)
    except (binascii.Error, ValueError):
        raise RoboWitnessException(
            status_code=422,
            code="INVALID_BASE64",
            message="content_base64 is not valid base64",
        )
    return inspect_evidence_zip(data)


@router.get("/{verification_id}", status_code=status.HTTP_200_OK)
def get_evidence_metadata(verification_id: str):
    v_dir = settings.artifacts_path / "verifications" / verification_id
    if not v_dir.exists():
        raise RoboWitnessException(
            status_code=404,
            code="EVIDENCE_NOT_FOUND",
            message=f"Evidence package {verification_id} not found on disk",
        )

    manifest_file = v_dir / "manifest.json"
    hashes_file = v_dir / "hashes.json"

    manifest_data = {}
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

    hashes_data = {}
    if hashes_file.exists():
        with open(hashes_file, "r", encoding="utf-8") as f:
            hashes_data = json.load(f)

    files = [p.name for p in v_dir.iterdir() if p.is_file()]

    return {
        "verification_id": verification_id,
        "files": files,
        "manifest": manifest_data,
        "hashes": hashes_data,
    }


@router.get("/{verification_id}/download")
def download_evidence_zip(verification_id: str):
    v_dir = settings.artifacts_path / "verifications" / verification_id
    # Path traversal safety check
    try:
        resolved = v_dir.resolve()
        artifacts_root = settings.artifacts_path.resolve()
        if not str(resolved).startswith(str(artifacts_root)):
            raise RoboWitnessException(
                status_code=403, code="FORBIDDEN_PATH", message="Access denied"
            )
    except Exception:
        raise RoboWitnessException(status_code=403, code="FORBIDDEN_PATH", message="Access denied")

    if not resolved.exists():
        raise RoboWitnessException(
            status_code=404,
            code="EVIDENCE_NOT_FOUND",
            message=f"Evidence package {verification_id} not found",
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in resolved.rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(resolved)
                zf.write(file_path, arcname=str(rel_path))

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=evidence_{verification_id}.zip"},
    )
