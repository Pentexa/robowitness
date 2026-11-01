"""Local user-policy API: list available policy files and the gate state."""

from fastapi import APIRouter, status
from app.policies.local_registry import list_local_policies

router = APIRouter(prefix="/local-policies", tags=["Local Policies"])


@router.get("", status_code=status.HTTP_200_OK)
def get_local_policies():
    return list_local_policies()
