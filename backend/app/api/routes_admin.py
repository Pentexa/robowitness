"""Enterprise admin API: workspace metrics, audit trail, backup/restore."""

import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import List, Literal
from fastapi import APIRouter, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from app.db import get_db
from app.errors import RoboWitnessException
from app.security import current_principal, current_workspace, list_audit

router = APIRouter(tags=["Admin"])


class ApiKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=80)
    role: Literal["admin", "editor", "viewer"] = "viewer"
    workspace_id: str = Field(default="default", min_length=1, max_length=80)


@router.post("/admin/api-keys", status_code=status.HTTP_201_CREATED)
def create_api_key(body: ApiKeyCreate, request: Request):
    """Create a DB-managed API key. The plaintext is shown ONCE, here only."""
    _require_admin(request)
    # Lockout guard: the very first active key must be admin, otherwise the
    # operator locks themselves out of key management the moment auth turns on.
    with get_db() as conn:
        active = conn.execute("SELECT COUNT(*) FROM api_keys WHERE revoked_at IS NULL").fetchone()[
            0
        ]
    if active == 0 and body.role != "admin":
        raise RoboWitnessException(
            status_code=422,
            code="FIRST_KEY_MUST_BE_ADMIN",
            message="The first API key must have the admin role (lockout prevention)",
        )
    plaintext = "rw_" + secrets.token_urlsafe(32)
    key_id = f"key-{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (key_id, key_hash, label, role_name, workspace_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                key_id,
                hashlib.sha256(plaintext.encode()).hexdigest(),
                body.label,
                body.role,
                body.workspace_id,
                now,
            ),
        )
        conn.commit()
    return {
        "key_id": key_id,
        "api_key": plaintext,
        "label": body.label,
        "role": body.role,
        "workspace_id": body.workspace_id,
        "created_at": now,
        "note": "Bu anahtar bir daha gösterilmez; hemen kaydedin.",
    }


@router.get("/admin/api-keys", status_code=status.HTTP_200_OK)
def list_api_keys(request: Request):
    _require_admin(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT key_id, label, role_name, workspace_id, created_at, revoked_at "
            "FROM api_keys ORDER BY created_at DESC"
        ).fetchall()
    return {"keys": [dict(r) for r in rows]}


@router.delete("/admin/api-keys/{key_id}", status_code=status.HTTP_200_OK)
def revoke_api_key(key_id: str, request: Request):
    _require_admin(request)
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE api_keys SET revoked_at = ? WHERE key_id = ? AND revoked_at IS NULL",
            (now, key_id),
        )
        conn.commit()
    if cur.rowcount == 0:
        raise RoboWitnessException(
            status_code=404, code="API_KEY_NOT_FOUND", message=f"API key {key_id} does not exist"
        )
    return {"revoked": key_id}


def _require_admin(request: Request) -> None:
    if current_principal(request).role != "admin":
        raise RoboWitnessException(
            status_code=403,
            code="FORBIDDEN_ROLE",
            message="This operation requires admin role",
        )


def _workspace_rows(table: str, workspace: str) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE workspace_id = ?", (workspace,)
        ).fetchall()
    return [dict(r) for r in rows]


@router.get("/prom", status_code=status.HTTP_200_OK)
def prometheus_metrics():
    """Prometheus text exposition for jobs/runs/batteries (no labels explosion)."""
    from fastapi.responses import PlainTextResponse

    with get_db() as conn:
        job_rows = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
        battery_total = conn.execute("SELECT COUNT(*) FROM battery_runs").fetchone()[0]
        run_rows = conn.execute(
            "SELECT oracle_status, COUNT(*) FROM runs GROUP BY oracle_status"
        ).fetchall()
        import_total = conn.execute("SELECT COUNT(*) FROM telemetry_imports").fetchone()[0]
    lines = [
        "# TYPE robowitness_jobs gauge",
        *[f'robowitness_jobs{{status="{r[0]}"}} {r[1]}' for r in job_rows],
        "# TYPE robowitness_batteries_total gauge",
        f"robowitness_batteries_total {battery_total}",
        "# TYPE robowitness_runs gauge",
        *[f'robowitness_runs{{oracle_status="{r[0]}"}} {r[1]}' for r in run_rows],
        "# TYPE robowitness_telemetry_imports_total gauge",
        f"robowitness_telemetry_imports_total {import_total}",
        "",
    ]
    return PlainTextResponse(content="\n".join(lines), media_type="text/plain")


@router.get("/metrics", status_code=status.HTTP_200_OK)
def get_metrics(request: Request):
    ws = current_workspace(request)
    with get_db() as conn:

        def count(sql: str, params: tuple = ()) -> int:
            return conn.execute(sql, params).fetchone()[0]

        batteries = count("SELECT COUNT(*) FROM battery_runs WHERE workspace_id = ?", (ws,))
        last = conn.execute(
            "SELECT result_json FROM battery_runs WHERE workspace_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (ws,),
        ).fetchone()
        imports = conn.execute(
            "SELECT result_json FROM telemetry_imports WHERE workspace_id = ?", (ws,)
        ).fetchall()

    from app.schemas.battery import BatteryResult
    from app.schemas.telemetry_import import TelemetryImportResult

    import_results = [TelemetryImportResult.model_validate_json(r["result_json"]) for r in imports]
    return {
        "workspace_id": ws,
        "robots_user": count_workspace_robots(ws),
        "policy_profiles_user": _count("policy_profiles", ws),
        "batteries": batteries,
        "last_battery_summary": (
            BatteryResult.model_validate_json(last["result_json"]).summary.model_dump()
            if last
            else None
        ),
        "telemetry_imports": len(import_results),
        "telemetry_imports_pass": sum(1 for r in import_results if r.oracle_status == "PASS"),
        "telemetry_imports_fail": sum(1 for r in import_results if r.oracle_status == "FAIL"),
        "runs_total": _count_all("runs"),
        "verifications_total": _count_all("verifications"),
        "jobs_by_status": _jobs_by_status(),
    }


def _count(table: str, workspace: str) -> int:
    with get_db() as conn:
        return conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE workspace_id = ?", (workspace,)
        ).fetchone()[0]


def _count_all(table: str) -> int:
    with get_db() as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def count_workspace_robots(workspace: str) -> int:
    return _count("robots", workspace)


def _jobs_by_status() -> dict:
    with get_db() as conn:
        rows = conn.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status").fetchall()
    return {r[0]: r[1] for r in rows}


@router.get("/audit", status_code=status.HTTP_200_OK)
def get_audit(request: Request, limit: int = Query(50, ge=1, le=200)):
    principal = current_principal(request)
    if principal.role != "admin":
        raise RoboWitnessException(
            status_code=403,
            code="FORBIDDEN_ROLE",
            message="Audit trail requires admin role",
        )
    return {"workspace_id": principal.workspace, "entries": list_audit(limit, principal.workspace)}


class RetentionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    older_than_days: int = Field(default=30, ge=1, le=3650)
    dry_run: bool = True


@router.post("/admin/backup", status_code=status.HTTP_201_CREATED)
def create_backup(request: Request):
    """Consistent SQLite backup file with SHA-256 (WAL-safe backup API)."""
    import hashlib
    import sqlite3 as _sqlite3

    _require_admin(request)
    from app.config import settings

    backup_dir = settings.artifacts_path / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = backup_dir / f"robowitness-{stamp}.sqlite3"
    src = _sqlite3.connect(str(settings.db_path))
    try:
        dst = _sqlite3.connect(str(target))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {"file": target.name, "sha256": digest, "bytes": target.stat().st_size}


class RestoreRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    file: str = Field(min_length=1, max_length=200)


@router.post("/admin/restore", status_code=status.HTTP_200_OK)
def restore_backup(body: RestoreRequest, request: Request):
    """Restore the DB from a named backup in artifacts/backups.

    Safety: the current DB is first copied to a pre-restore backup, and the
    chosen file's SHA-256 is returned so the operator can verify what was
    restored. Takes effect for new connections; restart services afterwards.
    """
    import hashlib
    import sqlite3 as _sqlite3

    _require_admin(request)
    from app.config import settings

    backup_dir = (settings.artifacts_path / "backups").resolve()
    target = (backup_dir / body.file).resolve()
    if target.parent != backup_dir or not target.exists():
        raise RoboWitnessException(
            status_code=404, code="BACKUP_NOT_FOUND", message=f"Backup {body.file} not found"
        )
    digest = hashlib.sha256(target.read_bytes()).hexdigest()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safety = backup_dir / f"pre-restore-{stamp}.sqlite3"
    src = _sqlite3.connect(str(settings.db_path))
    try:
        dst = _sqlite3.connect(str(safety))
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()

    restore_src = _sqlite3.connect(str(target))
    try:
        live = _sqlite3.connect(str(settings.db_path))
        try:
            restore_src.backup(live)
        finally:
            live.close()
    finally:
        restore_src.close()
    return {"restored_from": body.file, "sha256": digest, "safety_backup": safety.name}


@router.get("/admin/backups", status_code=status.HTTP_200_OK)
def list_backups(request: Request):
    _require_admin(request)
    from app.config import settings

    backup_dir = settings.artifacts_path / "backups"
    files = []
    if backup_dir.exists():
        for path in sorted(backup_dir.glob("*.sqlite3"), reverse=True):
            files.append({"file": path.name, "bytes": path.stat().st_size})
    return {"backups": files}


@router.post("/admin/retention", status_code=status.HTTP_200_OK)
def apply_retention(body: RetentionRequest, request: Request):
    """Delete old tenant history (batteries/imports/audit + finished jobs).

    Run artifacts and verifications are sealed evidence and are NOT touched.
    """
    _require_admin(request)
    from datetime import timedelta as _timedelta

    cutoff = (datetime.now(timezone.utc) - _timedelta(days=body.older_than_days)).isoformat()
    counts: dict[str, int] = {}
    with get_db() as conn:
        for table in ("battery_runs", "telemetry_imports", "audit_logs"):
            counts[table] = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE created_at < ?", (cutoff,)
            ).fetchone()[0]
        counts["jobs"] = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE created_at < ? AND status IN "
            "('completed', 'failed', 'cancelled')",
            (cutoff,),
        ).fetchone()[0]
        if not body.dry_run:
            for table in ("battery_runs", "telemetry_imports", "audit_logs"):
                conn.execute(f"DELETE FROM {table} WHERE created_at < ?", (cutoff,))
            conn.execute(
                "DELETE FROM jobs WHERE created_at < ? AND status IN "
                "('completed', 'failed', 'cancelled')",
                (cutoff,),
            )
            conn.commit()
    return {"cutoff": cutoff, "dry_run": body.dry_run, "counts": counts}


class WorkspaceExport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str = "1.0"
    workspace_id: str
    exported_at: str
    robots: List[dict] = Field(default_factory=list)
    policy_profiles: List[dict] = Field(default_factory=list)
    batteries: List[dict] = Field(default_factory=list)
    telemetry_imports: List[dict] = Field(default_factory=list)


@router.get("/workspaces/export", response_model=WorkspaceExport, status_code=status.HTTP_200_OK)
def export_workspace(request: Request):
    """Full tenant-data backup for the caller's workspace (JSON bundle)."""
    _require_admin(request)
    ws = current_workspace(request)
    return WorkspaceExport(
        workspace_id=ws,
        exported_at=datetime.now(timezone.utc).isoformat(),
        robots=_workspace_rows("robots", ws),
        policy_profiles=_workspace_rows("policy_profiles", ws),
        batteries=_workspace_rows("battery_runs", ws),
        telemetry_imports=_workspace_rows("telemetry_imports", ws),
    )


class WorkspaceImportResult(BaseModel):
    inserted: dict
    skipped: dict


@router.post(
    "/workspaces/import", response_model=WorkspaceImportResult, status_code=status.HTTP_200_OK
)
def import_workspace(bundle: WorkspaceExport, request: Request):
    """Restore a bundle into the caller's workspace.

    Robots/profiles keep their ids when free, otherwise get fresh ids (their
    content is the identity that matters). Batteries/imports keep ids when
    free, otherwise are skipped and reported — history is never overwritten.
    """
    _require_admin(request)
    ws = current_workspace(request)
    inserted = {"robots": 0, "policy_profiles": 0, "batteries": 0, "telemetry_imports": 0}
    skipped = {"robots": 0, "policy_profiles": 0, "batteries": 0, "telemetry_imports": 0}
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        for row in bundle.robots:
            rid = row["robot_id"]
            exists = conn.execute("SELECT 1 FROM robots WHERE robot_id = ?", (rid,)).fetchone()
            if exists:
                rid = f"robot-{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO robots (robot_id, profile_json, created_at, updated_at, "
                "workspace_id) VALUES (?, ?, ?, ?, ?)",
                (rid, row["profile_json"], row.get("created_at") or now, now, ws),
            )
            inserted["robots"] += 1
        for row in bundle.policy_profiles:
            pid = row["profile_id"]
            exists = conn.execute(
                "SELECT 1 FROM policy_profiles WHERE profile_id = ?", (pid,)
            ).fetchone()
            if exists:
                pid = f"profile-{uuid.uuid4().hex[:12]}"
            conn.execute(
                "INSERT INTO policy_profiles (profile_id, profile_json, created_at, "
                "updated_at, workspace_id) VALUES (?, ?, ?, ?, ?)",
                (pid, row["profile_json"], row.get("created_at") or now, now, ws),
            )
            inserted["policy_profiles"] += 1
        for row in bundle.batteries:
            exists = conn.execute(
                "SELECT 1 FROM battery_runs WHERE battery_id = ?", (row["battery_id"],)
            ).fetchone()
            if exists:
                skipped["batteries"] += 1
                continue
            conn.execute(
                "INSERT INTO battery_runs (battery_id, robot_id, result_json, created_at, "
                "workspace_id) VALUES (?, ?, ?, ?, ?)",
                (row["battery_id"], row["robot_id"], row["result_json"], row["created_at"], ws),
            )
            inserted["batteries"] += 1
        for row in bundle.telemetry_imports:
            exists = conn.execute(
                "SELECT 1 FROM telemetry_imports WHERE import_id = ?", (row["import_id"],)
            ).fetchone()
            if exists:
                skipped["telemetry_imports"] += 1
                continue
            conn.execute(
                "INSERT INTO telemetry_imports (import_id, result_json, created_at, "
                "workspace_id) VALUES (?, ?, ?, ?)",
                (row["import_id"], row["result_json"], row["created_at"], ws),
            )
            inserted["telemetry_imports"] += 1
        conn.commit()
    return WorkspaceImportResult(inserted=inserted, skipped=skipped)
