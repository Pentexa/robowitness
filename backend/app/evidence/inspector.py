"""Independent evidence-ZIP inspection.

Accepts the bytes of an evidence package ZIP (as produced by the download
endpoint), extracts them to a throwaway directory with strict path/size
guards, and re-verifies integrity from scratch: hashes.json presence,
required members per package type, and a fresh SHA-256 of every sealed
file. Nothing here trusts the uploader's claims — status is recomputed.
"""

import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.evidence.integrity import compute_file_sha256, verify_package_integrity
from app.evidence.recorder import RUN_REQUIRED_FILES, VERIFICATION_REQUIRED_FILES

MAX_ZIP_BYTES = 25 * 1024 * 1024
MAX_MEMBERS = 64
MAX_MEMBER_BYTES = 50 * 1024 * 1024


class EvidenceInspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str = Field(default="evidence.zip", max_length=200)
    content_base64: str = Field(min_length=4, max_length=36_000_000)


class InspectedFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: str  # OK | MISMATCH | MISSING | NOT_SEALED | EXTRA
    sha256: Optional[str] = None
    expected_sha256: Optional[str] = None
    size_bytes: int = 0


class EvidenceInspectReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    package_type: str  # verification | run | unknown
    package_id: Optional[str] = None
    verdict: Optional[str] = None
    oracle_status: Optional[str] = None
    files: List[InspectedFile] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    file_count: int = 0


def _safe_member_name(name: str) -> Optional[str]:
    """Flat basenames only: evidence packages are single-directory by design.
    Any traversal segment, absolute path, or drive prefix is rejected
    outright — never silently renamed."""
    normalized = name.replace("\\", "/")
    if normalized.endswith("/"):
        return None
    segments = normalized.split("/")
    if any(seg in ("..", "") for seg in segments) or ":" in normalized[:3]:
        return None
    base = segments[-1]
    if not base or base == ".":
        return None
    return base


def inspect_evidence_zip(data: bytes) -> EvidenceInspectReport:
    errors: List[str] = []
    if len(data) > MAX_ZIP_BYTES:
        return EvidenceInspectReport(ok=False, package_type="unknown", errors=["ZIP_TOO_LARGE"])
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        return EvidenceInspectReport(ok=False, package_type="unknown", errors=["NOT_A_ZIP_FILE"])

    members = [m for m in archive.infolist() if not m.is_dir()]
    if len(members) > MAX_MEMBERS:
        return EvidenceInspectReport(ok=False, package_type="unknown", errors=["TOO_MANY_MEMBERS"])

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        root_resolved = root.resolve()
        extracted: dict[str, int] = {}
        for member in members:
            base = _safe_member_name(member.filename)
            if base is None:
                errors.append(f"UNSAFE_MEMBER_NAME_{member.filename}")
                continue
            if member.file_size > MAX_MEMBER_BYTES:
                errors.append(f"MEMBER_TOO_LARGE_{base}")
                continue
            target = (root / base).resolve()
            if target.parent != root_resolved:
                errors.append(f"UNSAFE_MEMBER_NAME_{member.filename}")
                continue
            target.write_bytes(archive.read(member))
            extracted[base] = member.file_size

        package_type = "unknown"
        package_id: Optional[str] = None
        verdict: Optional[str] = None
        oracle_status: Optional[str] = None
        manifest_path = root / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                if "verification_id" in manifest:
                    package_type = "verification"
                    package_id = manifest.get("verification_id")
                    verdict = manifest.get("verdict")
                elif "run_id" in manifest:
                    package_type = "run"
                    package_id = manifest.get("run_id")
                    oracle_status = manifest.get("oracle_status")
            except (ValueError, UnicodeDecodeError):
                errors.append("MANIFEST_UNREADABLE")

        required = (
            VERIFICATION_REQUIRED_FILES
            if package_type == "verification"
            else RUN_REQUIRED_FILES
            if package_type == "run"
            else []
        )
        integrity_ok, integrity_errors = verify_package_integrity(root, required)
        errors.extend(integrity_errors)

        stored_hashes: dict[str, str] = {}
        hashes_path = root / "hashes.json"
        if hashes_path.exists():
            try:
                stored_hashes = json.loads(hashes_path.read_text(encoding="utf-8"))
            except (ValueError, UnicodeDecodeError):
                errors.append("HASHES_JSON_UNREADABLE")

        files: List[InspectedFile] = []
        names = sorted(set(extracted) | set(stored_hashes) | set(required))
        for name in names:
            path = root / name
            expected = stored_hashes.get(name)
            if name in required and not path.exists():
                files.append(InspectedFile(name=name, status="MISSING", expected_sha256=expected))
            elif path.exists() and expected is None and name != "hashes.json":
                files.append(
                    InspectedFile(
                        name=name,
                        status="NOT_SEALED",
                        sha256=compute_file_sha256(path),
                        size_bytes=extracted.get(name, 0),
                    )
                )
            elif path.exists():
                actual = compute_file_sha256(path)
                files.append(
                    InspectedFile(
                        name=name,
                        status="OK" if actual == str(expected).lower() else "MISMATCH",
                        sha256=actual,
                        expected_sha256=expected,
                        size_bytes=extracted.get(name, 0),
                    )
                )
            else:
                files.append(InspectedFile(name=name, status="MISSING", expected_sha256=expected))

        ok = integrity_ok and not any(
            e.startswith(("UNSAFE_MEMBER_NAME", "MEMBER_TOO_LARGE")) for e in errors
        )
        return EvidenceInspectReport(
            ok=ok and len(errors) == 0,
            package_type=package_type,
            package_id=package_id,
            verdict=verdict,
            oracle_status=oracle_status,
            files=files,
            errors=errors,
            file_count=len(extracted),
        )
