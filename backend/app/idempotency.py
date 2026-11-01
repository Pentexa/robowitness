"""Idempotency-Key support for job-creating endpoints.

A client retrying with the same Idempotency-Key (same workspace + endpoint)
gets the originally created job back instead of enqueueing a duplicate.
"""

import json
from datetime import datetime, timezone

from fastapi import Request
from app.db import get_db
from app.schemas.jobs import JobCreateResponse
from app.security import current_workspace


def get_idempotent_response(request: Request) -> JobCreateResponse | None:
    key = request.headers.get("Idempotency-Key")
    if not key:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT response_json FROM idempotency_keys WHERE idem_key = ? AND workspace_id = ? "
            "AND endpoint = ?",
            (key, current_workspace(request), request.url.path),
        ).fetchone()
    if row is None:
        return None
    return JobCreateResponse.model_validate(json.loads(row["response_json"]))


def store_idempotent_response(request: Request, response: JobCreateResponse) -> None:
    key = request.headers.get("Idempotency-Key")
    if not key:
        return
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO idempotency_keys (idem_key, workspace_id, endpoint, "
            "response_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                key,
                current_workspace(request),
                request.url.path,
                response.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
