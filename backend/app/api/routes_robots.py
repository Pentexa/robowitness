"""Robot catalog API routes: brand/model/features, add/edit/delete robots."""

from typing import List
from fastapi import APIRouter, Request, status
from app.errors import RoboWitnessException
from app.robots import repository
from app.security import current_workspace
from app.schemas.robot_profile import RobotProfile, RobotProfileCreate
from app.schemas.scenario import ScenarioSpec

router = APIRouter(prefix="/robots", tags=["Robots"])


def _not_found(robot_id: str) -> RoboWitnessException:
    return RoboWitnessException(
        status_code=404, code="ROBOT_NOT_FOUND", message=f"Robot {robot_id} does not exist"
    )


@router.get("", response_model=List[RobotProfile], status_code=status.HTTP_200_OK)
def list_robots(request: Request):
    return repository.list_robots(current_workspace(request))


@router.post("", response_model=RobotProfile, status_code=status.HTTP_201_CREATED)
def create_robot(body: RobotProfileCreate, request: Request):
    duplicate = repository.find_duplicate(body, workspace=current_workspace(request))
    if duplicate is not None:
        raise RoboWitnessException(
            status_code=409,
            code="ROBOT_ALREADY_EXISTS",
            message=f"A robot with brand/model/variant already exists: {duplicate.robot_id}",
        )
    return repository.create_robot(body, current_workspace(request))


@router.get("/{robot_id}", response_model=RobotProfile, status_code=status.HTTP_200_OK)
def get_robot(robot_id: str, request: Request):
    robot = repository.get_robot(robot_id, current_workspace(request))
    if robot is None:
        raise _not_found(robot_id)
    return robot


@router.put("/{robot_id}", response_model=RobotProfile, status_code=status.HTTP_200_OK)
def update_robot(robot_id: str, body: RobotProfileCreate, request: Request):
    ws = current_workspace(request)
    existing = repository.get_robot(robot_id, ws)
    if existing is None:
        raise _not_found(robot_id)
    if existing.source == "builtin":
        raise RoboWitnessException(
            status_code=403,
            code="ROBOT_BUILTIN_READONLY",
            message="Built-in catalog robots cannot be edited; add a user copy instead",
        )
    duplicate = repository.find_duplicate(body, exclude_id=robot_id, workspace=ws)
    if duplicate is not None:
        raise RoboWitnessException(
            status_code=409,
            code="ROBOT_ALREADY_EXISTS",
            message=f"A robot with brand/model/variant already exists: {duplicate.robot_id}",
        )
    updated = repository.update_robot(robot_id, body, ws)
    if updated is None:
        raise _not_found(robot_id)
    return updated


@router.delete("/{robot_id}", status_code=status.HTTP_200_OK)
def delete_robot(robot_id: str, request: Request):
    ws = current_workspace(request)
    existing = repository.get_robot(robot_id, ws)
    if existing is None:
        raise _not_found(robot_id)
    if existing.source == "builtin":
        raise RoboWitnessException(
            status_code=403,
            code="ROBOT_BUILTIN_READONLY",
            message="Built-in catalog robots cannot be deleted",
        )
    repository.delete_robot(robot_id, ws)
    return {"deleted": robot_id}


@router.post(
    "/{robot_id}/apply-to-scenario",
    response_model=ScenarioSpec,
    status_code=status.HTTP_200_OK,
)
def apply_to_scenario(robot_id: str, scenario: ScenarioSpec, request: Request):
    robot = repository.get_robot(robot_id, current_workspace(request))
    if robot is None:
        raise _not_found(robot_id)
    if not robot.simulation_compatible:
        raise RoboWitnessException(
            status_code=422,
            code="ROBOT_NOT_SIM_COMPATIBLE",
            message=(
                "This robot cannot drive the differential-drive simulator: "
                + ", ".join(robot.compatibility_issues)
            ),
        )
    return repository.apply_profile_to_scenario(robot, scenario)
