"""Policy profile API: named presets for the 5 numeric policy parameters."""

from typing import List
from fastapi import APIRouter, status
from app.errors import RoboWitnessException
from app.policies import profile_repository as repo
from app.schemas.policy_profile import PolicyProfile, PolicyProfileCreate

router = APIRouter(prefix="/policy-profiles", tags=["Policy Profiles"])


def _not_found(profile_id: str) -> RoboWitnessException:
    return RoboWitnessException(
        status_code=404,
        code="POLICY_PROFILE_NOT_FOUND",
        message=f"Policy profile {profile_id} does not exist",
    )


def _builtin_guard(profile: PolicyProfile) -> None:
    if profile.source == "builtin":
        raise RoboWitnessException(
            status_code=403,
            code="POLICY_PROFILE_BUILTIN_READONLY",
            message="Built-in policy profiles cannot be edited or deleted",
        )


@router.get("", response_model=List[PolicyProfile], status_code=status.HTTP_200_OK)
def list_profiles():
    return repo.list_profiles()


@router.post("", response_model=PolicyProfile, status_code=status.HTTP_201_CREATED)
def create_profile(request: PolicyProfileCreate):
    if repo.find_duplicate(request.name) is not None:
        raise RoboWitnessException(
            status_code=409,
            code="POLICY_PROFILE_ALREADY_EXISTS",
            message=f"A policy profile named '{request.name}' already exists",
        )
    return repo.create_profile(request)


@router.get("/{profile_id}", response_model=PolicyProfile, status_code=status.HTTP_200_OK)
def get_profile(profile_id: str):
    profile = repo.get_profile(profile_id)
    if profile is None:
        raise _not_found(profile_id)
    return profile


@router.put("/{profile_id}", response_model=PolicyProfile, status_code=status.HTTP_200_OK)
def update_profile(profile_id: str, request: PolicyProfileCreate):
    existing = repo.get_profile(profile_id)
    if existing is None:
        raise _not_found(profile_id)
    _builtin_guard(existing)
    if repo.find_duplicate(request.name, exclude_id=profile_id) is not None:
        raise RoboWitnessException(
            status_code=409,
            code="POLICY_PROFILE_ALREADY_EXISTS",
            message=f"A policy profile named '{request.name}' already exists",
        )
    updated = repo.update_profile(profile_id, request)
    if updated is None:
        raise _not_found(profile_id)
    return updated


@router.delete("/{profile_id}", status_code=status.HTTP_200_OK)
def delete_profile(profile_id: str):
    existing = repo.get_profile(profile_id)
    if existing is None:
        raise _not_found(profile_id)
    _builtin_guard(existing)
    repo.delete_profile(profile_id)
    return {"deleted": profile_id}
