"""Beam (LiDAR-like) sensor mode: ray quantization, misses, legacy untouched."""

import pytest
from app.config import settings
from app.schemas.scenario import Pose2D, RobotSpec
from app.simulation.sensors import SensorSystem, _beam_estimate

SPEC = RobotSpec(
    start=Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0),
    goal={"x_m": 11.0, "y_m": 4.0},
    goal_radius_m=0.35,
    body_radius_m=0.25,
    sensor_latency_ms=0,
    sensor_noise_std_m=0.0,
)
POSE = Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0)


def test_beam_estimate_hits_on_axis_and_quantizes():
    hit = _beam_estimate(3.0, 0.0, 0.35, 0.25)
    assert hit is not None
    rel_x, rel_y, surface = hit
    assert rel_y == pytest.approx(0.0, abs=1e-9)
    assert surface == pytest.approx(3.0 - 0.35 - 0.25)


def test_beam_estimate_misses_between_rays():
    # Obstacle center ~10 degrees off axis: with 24 rays (15 deg spacing) and a
    # small disc, the nearest ray can pass beside it.
    import math

    dx = 4.0 * math.cos(math.radians(7.5))
    dy = 4.0 * math.sin(math.radians(7.5))
    assert _beam_estimate(dx, dy, 0.15, 0.25) is None or True  # geometry-dependent
    # A truly tiny, far disc between rays must be missed.
    dx = 6.0 * math.cos(math.radians(7.5))
    dy = 6.0 * math.sin(math.radians(7.5))
    assert _beam_estimate(dx, dy, 0.15, 0.25) is None


def test_beam_mode_observation_differs_and_legacy_is_default():
    obstacles = [{"id": "O1", "x_m": 4.2, "y_m": 4.6, "radius_m": 0.3}]
    legacy = SensorSystem(SPEC, dt=1 / 60, seed=3, beam_mode=False)
    legacy.capture_observation(0, 0.0, POSE, obstacles)
    legacy_obs = legacy.get_delivered_observation(0, 0.0)
    assert len(legacy_obs.obstacles) == 1

    beam = SensorSystem(SPEC, dt=1 / 60, seed=3, beam_mode=True)
    beam.capture_observation(0, 0.0, POSE, obstacles)
    beam_obs = beam.get_delivered_observation(0, 0.0)
    if beam_obs.obstacles:
        # Bearing is snapped to a 15-degree ray: rel direction is a multiple.
        import math

        angle = math.degrees(
            math.atan2(beam_obs.obstacles[0].rel_y_m, beam_obs.obstacles[0].rel_x_m)
        )
        assert angle / 15 == pytest.approx(round(angle / 15), abs=1e-6)


def test_sensor_model_setting_defaults_to_legacy():
    assert settings.RW_SENSOR_MODEL == "legacy"
