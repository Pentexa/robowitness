"""Health and system status routes."""
import os
import sqlite3
from fastapi import APIRouter, status
from pydantic import BaseModel
from app.config import settings

router = APIRouter(prefix="/health", tags=["Health"])

class HealthResponse(BaseModel):
    status: str
    schema_version: str
    db_status: str
    worker_active: bool
    ai_mode: str

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

    return HealthResponse(
        status="healthy",
        schema_version="1.0",
        db_status=db_status,
        worker_active=True,
        ai_mode=settings.RW_AI_MODE,
    )
