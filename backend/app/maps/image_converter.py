"""Explicit overhead-image calibration into the existing circular 2D world."""

import hashlib
import math

from app.schemas.image_scenario import ImageDetectionResult, ImageScenarioRequest
from app.schemas.scenario import ScenarioSpec


def image_to_scenario(detection: ImageDetectionResult, request: ImageScenarioRequest):
    by_id = {d.id: d for d in detection.detections}
    if any(i not in by_id for i in request.selected_ids):
        raise ValueError("Selected object was not detected in this image")
    obstacles = []
    warnings = [
        "User-calibrated overhead projection; image boxes become enclosing static circles. "
        "Depth, hidden objects and motion cannot be inferred from a still image."
    ]
    for index, object_id in enumerate(request.selected_ids):
        box = by_id[object_id].box
        sx = request.width_m / detection.image_width
        sy = request.height_m / detection.image_height
        x = (box.left + box.right) * 0.5 * sx
        y = request.height_m - (box.top + box.bottom) * 0.5 * sy
        radius = math.hypot((box.right - box.left) * sx, (box.bottom - box.top) * sy) / 2
        if radius > 0.8:
            raise ValueError(
                f"Object {index + 1} needs radius {radius:.2f} m (maximum 0.80 m). "
                "Review the scale or deselect this object; it will not be shrunk."
            )
        if radius < 0.15:
            radius = 0.15
            warnings.append(f"Object {index + 1}: expanded to simulator minimum radius 0.15 m.")
        position = {"x_m": x, "y_m": y}
        obstacles.append(
            {
                "id": f"IMG-O{index + 1}",
                "shape": "circle",
                "radius_m": radius,
                "motion": "static",
                "start": position,
                "end": position,
                "speed_mps": 0,
            }
        )
    start = {
        "x_m": request.start.x * request.width_m,
        "y_m": (1 - request.start.y) * request.height_m,
    }
    goal = {"x_m": request.goal.x * request.width_m, "y_m": (1 - request.goal.y) * request.height_m}
    if math.hypot(start["x_m"] - goal["x_m"], start["y_m"] - goal["y_m"]) < 0.7:
        raise ValueError("Choose distinct start and goal points at least 0.70 m apart")
    for obs in obstacles:
        if (
            math.hypot(goal["x_m"] - obs["start"]["x_m"], goal["y_m"] - obs["start"]["y_m"])
            < obs["radius_m"] + 0.35
        ):
            raise ValueError("Goal overlaps an obstacle; choose another goal on the image")
    identity = hashlib.sha256(request.model_dump_json(exclude={"save"}).encode()).hexdigest()[:16]
    spec = ScenarioSpec.model_validate(
        {
            "id": f"RW-IMG-{identity}",
            "kind": "static_obstacle",
            "seed": 1842,
            "world": {
                "width_m": request.width_m,
                "height_m": request.height_m,
                "duration_limit_s": 30,
            },
            "robot": {
                "start": {
                    **start,
                    "yaw_rad": math.atan2(goal["y_m"] - start["y_m"], goal["x_m"] - start["x_m"]),
                },
                "goal": goal,
                "goal_radius_m": 0.35,
                "body_radius_m": 0.25,
                "sensor_latency_ms": 450,
                "sensor_noise_std_m": 0,
            },
            "obstacles": obstacles,
            "oracle": {"max_duration_s": 30},
        }
    )
    return spec, warnings
