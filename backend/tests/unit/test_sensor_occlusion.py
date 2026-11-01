"""Sensor occlusion: an obstacle behind a closer one must not be observed."""

from app.schemas.scenario import Pose2D, RobotSpec
from app.simulation.sensors import SensorSystem, _is_occluded

SPEC = RobotSpec(
    start=Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0),
    goal={"x_m": 11.0, "y_m": 4.0},
    goal_radius_m=0.35,
    body_radius_m=0.25,
    sensor_latency_ms=0,
    sensor_noise_std_m=0.0,
)

POSE = Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0)


def _obstacles():
    return [
        {"id": "NEAR", "x_m": 3.0, "y_m": 4.0, "radius_m": 0.4},
        {"id": "FAR", "x_m": 5.0, "y_m": 4.0, "radius_m": 0.4},
        {"id": "SIDE", "x_m": 4.0, "y_m": 6.0, "radius_m": 0.4},
    ]


def test_occlusion_geometry():
    obstacles = _obstacles()
    assert _is_occluded(1, obstacles, POSE) is True  # FAR hidden behind NEAR
    assert _is_occluded(0, obstacles, POSE) is False  # NEAR itself visible
    assert _is_occluded(2, obstacles, POSE) is False  # SIDE off the ray


def test_delivered_observation_hides_occluded_obstacle():
    system = SensorSystem(SPEC, dt=1.0 / 60.0, seed=7)
    system.capture_observation(0, 0.0, POSE, _obstacles())
    delivered = system.get_delivered_observation(0, 0.0)
    seen_ids = {o.id for o in delivered.obstacles}
    assert "NEAR" in seen_ids
    assert "SIDE" in seen_ids
    assert "FAR" not in seen_ids
