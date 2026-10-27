"""Standard error definitions and response models."""
import uuid
from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from pydantic import BaseModel, Field

class ErrorDetail(BaseModel):
    field: Optional[str] = None
    reason: str

class ErrorBody(BaseModel):
    code: str
    message: str
    details: List[ErrorDetail] = Field(default_factory=list)
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class ErrorEnvelope(BaseModel):
    error: ErrorBody

class RoboWitnessException(HTTPException):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[List[Dict[str, Any]]] = None,
    ):
        structured_details = [
            ErrorDetail(field=d.get("field"), reason=d.get("reason", "error"))
            for d in (details or [])
        ]
        body = ErrorEnvelope(
            error=ErrorBody(
                code=code,
                message=message,
                details=structured_details,
            )
        )
        super().__init__(status_code=status_code, detail=body.model_dump())
