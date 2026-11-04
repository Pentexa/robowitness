"""Enterprise security: API keys, roles, workspaces, audit trail.

Auth is opt-in: with no RW_API_KEYS configured the API stays open for local
use (actor=local, role=admin). When keys are configured, every /api call
(except /api/health) needs header X-API-Key. Key format in RW_API_KEYS:
  "key1:admin:workspace-a;key2:viewer:workspace-a;key3:editor:default"
Roles: admin (all) > editor (read+write) > viewer (read only).
Workspace isolation applies to tenant resources (robots, policy profiles,
batteries, telemetry imports). Builtin catalog entries are shared.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Request
from app.config import settings
from app.db import get_db

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
PUBLIC_PATHS = {"/api/health", "/api/prom"}


@dataclass
class Principal:
    actor: str
    role: str
    workspace: str


def parse_api_keys() -> dict[str, Principal]:
    keys: dict[str, Principal] = {}
    raw = (settings.RW_API_KEYS or "").strip()
    if not raw:
        return keys
    for entry in raw.split(";"):
        entry = entry.strip()
        if not entry:
            continue
        parts = [p.strip() for p in entry.split(":")]
        if len(parts) < 2:
            continue
        key, role = parts[0], parts[1]
        workspace = parts[2] if len(parts) > 2 and parts[2] else "default"
        if role not in ("admin", "editor", "viewer"):
            continue
        # codeql[py/weak-sensitive-data-hashing] -- short actor-label
        # fingerprint only; the key itself is never stored or verified here.
        actor = "key-" + hashlib.sha256(key.encode()).hexdigest()[:8]
        keys[key] = Principal(actor=actor, role=role, workspace=workspace)
    return keys


def auth_enabled() -> bool:
    return auth_configured()


def _db_api_keys() -> list[tuple[str, Principal]]:
    """Database-managed API keys (hashes only), managed via /api/admin/api-keys."""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT key_hash, label, role_name, workspace_id FROM api_keys "
                "WHERE revoked_at IS NULL"
            ).fetchall()
    except Exception:
        return []
    return [
        (
            row["key_hash"],
            Principal(
                actor=f"dbkey:{row['label']}", role=row["role_name"], workspace=row["workspace_id"]
            ),
        )
        for row in rows
    ]


def auth_configured() -> bool:
    return bool(
        parse_api_keys() or settings.RW_JWT_SECRET or settings.RW_OIDC_JWKS_URL or _db_api_keys()
    )


def authenticate(request: Request) -> Principal | None:
    """Resolve the caller; None means authentication failed (401 required)."""
    if not auth_configured():
        workspace = request.headers.get("X-Workspace-Id") or "default"
        return Principal(actor="local", role="admin", workspace=workspace)

    # Bearer JWT (HS256 shared secret or OIDC RS256) takes precedence.
    authorization = request.headers.get("Authorization") or ""
    if authorization.lower().startswith("bearer "):
        from app.jwt_auth import verify_jwt

        principal = verify_jwt(authorization[7:].strip())
        if principal is not None:
            return principal

    provided = request.headers.get("X-API-Key") or ""
    for key, principal in parse_api_keys().items():
        if hmac.compare_digest(provided, key):
            return principal
    if provided:
        # codeql[py/weak-sensitive-data-hashing] -- stored form of
        # high-entropy random API tokens (not passwords); compared with
        # hmac.compare_digest below. Slow KDFs are for human passwords.
        provided_hash = hashlib.sha256(provided.encode()).hexdigest()
        for key_hash, principal in _db_api_keys():
            if hmac.compare_digest(provided_hash, key_hash):
                return principal
    return None


def current_workspace(request: Request) -> str:
    principal = getattr(request.state, "principal", None)
    if principal is not None:
        return principal.workspace
    return request.headers.get("X-Workspace-Id") or "default"


def current_principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if principal is not None:
        return principal
    return Principal(actor="local", role="admin", workspace=current_workspace(request))


def write_audit(request: Request, status_code: int) -> None:
    """Append one audit row for mutating calls; best-effort, never breaks API."""
    if request.method not in WRITE_METHODS:
        return
    try:
        principal = current_principal(request)
        with get_db() as conn:
            conn.execute(
                "INSERT INTO audit_logs (actor, role_name, workspace_id, method, path, "
                "status_code, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    principal.actor,
                    principal.role,
                    principal.workspace,
                    request.method,
                    str(request.url.path),
                    status_code,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
    except Exception:
        pass


def list_audit(limit: int = 50, workspace: str | None = None) -> list[dict]:
    with get_db() as conn:
        if workspace:
            rows = conn.execute(
                "SELECT * FROM audit_logs WHERE workspace_id = ? ORDER BY created_at DESC LIMIT ?",
                (workspace, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]


__all__ = [
    "Principal",
    "parse_api_keys",
    "auth_enabled",
    "authenticate",
    "current_workspace",
    "current_principal",
    "write_audit",
    "list_audit",
]
