"""Health and system status routes."""

import sqlite3
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, status
from pydantic import BaseModel
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

WORKER_HEARTBEAT_STALE_S = 30.0


class HealthResponse(BaseModel):
    status: str
    schema_version: str
    db_status: str
    worker_active: bool
    worker_last_seen: Optional[str] = None
    ai_mode: str


def _worker_heartbeat() -> tuple[bool, Optional[str]]:
    hb = settings.artifacts_path / "worker_heartbeat.json"
    try:
        if not hb.exists():
            return False, None
        import json

        data = json.loads(hb.read_text(encoding="utf-8"))
        ts = data.get("ts")
        if not ts:
            return False, None
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds()
        return (age <= WORKER_HEARTBEAT_STALE_S), ts
    except Exception:
        return False, None


@router.get("", response_model=HealthResponse, status_code=status.HTTP_200_OK)
def get_health():
    db_status = "ok"
    try:
        if settings.db_path.exists():
            conn = sqlite3.connect(str(settings.db_path), timeout=2.0)
            conn.execute("SELECT 1")
            conn.close()
        else:
            db_status = "uninitialized"
    except Exception as e:
        db_status = f"error: {str(e)}"

    worker_active, worker_last_seen = _worker_heartbeat()

    return HealthResponse(
        status="healthy",
        schema_version="1.0",
        db_status=db_status,
        worker_active=worker_active,
        worker_last_seen=worker_last_seen,
        ai_mode=settings.RW_AI_MODE,
    )
