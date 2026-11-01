"""Simulation semantics tests: tick order, obstacle trajectory, sensor delay/noise, cleanup."""

import math
import pybullet as p
import pytest
from app.schemas.scenario import ScenarioSpec
from app.simulation.obstacles import SimObstacle
from app.simulation.sensors import SensorSystem
from app.simulation.world import SimulationWorld
from app.simulation.runner import SimulationRunner
from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.verification.oracle import evaluate_oracle
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent


@pytest.fixture
def client_id():
    cid = p.connect(p.DIRECT)
    try:
        yield cid
    finally:
        try:
            p.disconnect(physicsClientId=cid)
        except Exception:
            pass


def _ref_spec() -> ScenarioSpec:
    return ScenarioSpec.model_validate_json(
        (ROOT / "scenarios" / "reference" / "moving_obstacle_latency.json").read_text()
    )


def test_fixed_tick_is_1_60_and_max_ticks_consistent():
    spec = _ref_spec()
    assert spec.world.fixed_timestep_s == pytest.approx(1.0 / 60.0)
    runner = SimulationRunner(spec, PolicyConfig(), configurable_policy)
    assert runner.dt == pytest.approx(1.0 / 60.0)
    assert runner.max_ticks == int(spec.world.duration_limit_s / runner.dt) == 1800


def test_obstacle_ping_pong_endpoints_and_reversal(client_id):
    spec = _ref_spec()
    obs = SimObstacle(spec.obstacles[0], client_id)
    try:
        x0, y0 = obs.update_position(0.0)
        assert (x0, y0) == pytest.approx((spec.obstacles[0].start.x_m, spec.obstacles[0].start.y_m))
        half = obs.half_period_s
        assert half > 0
        x1, y1 = obs.update_position(half)
        assert (x1, y1) == pytest.approx((spec.obstacles[0].end.x_m, spec.obstacles[0].end.y_m))
        # Full period returns to start (reversal)
        x2, y2 = obs.update_position(2.0 * half)
        assert (x2, y2) == pytest.approx((spec.obstacles[0].start.x_m, spec.obstacles[0].start.y_m))
        # Midpoint is halfway
        xm, ym = obs.update_position(half / 2.0)
        assert xm == pytest.approx((spec.obstacles[0].start.x_m + spec.obstacles[0].end.x_m) / 2.0)
    finally:
        p.removeBody(obs.body_id, physicsClientId=client_id)


def test_sensor_latency_tick_rounding():
    spec = _ref_spec()
    dt = spec.world.fixed_timestep_s
    assert math.ceil((450 / 1000.0) / dt) == 27
    assert math.ceil((0 / 1000.0) / dt) == 0
    assert math.ceil((1000 / 1000.0) / dt) == 60
    sys = SensorSystem(spec.robot, dt, spec.seed)
    assert sys.latency_ticks == 27


def test_first_tick_observation_not_ready():
    spec = _ref_spec()
    sys = SensorSystem(spec.robot, spec.world.fixed_timestep_s, spec.seed)
    from app.schemas.scenario import Pose2D

    pose = Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0)
    sys.capture_observation(0, 0.0, pose, [])
    delivered = sys.get_delivered_observation(0, 0.0)
    assert delivered.valid is False
    assert delivered.obstacles == []


def test_zero_latency_delivers_immediately():
    spec = _ref_spec()
    spec.robot.sensor_latency_ms = 0
    sys = SensorSystem(spec.robot, spec.world.fixed_timestep_s, spec.seed)
    from app.schemas.scenario import Pose2D

    pose = Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0)
    sys.capture_observation(5, 5 * spec.world.fixed_timestep_s, pose, [])
    delivered = sys.get_delivered_observation(5, 5 * spec.world.fixed_timestep_s)
    assert delivered.valid is True
    assert delivered.sample_tick == 5
    assert delivered.age_s == pytest.approx(0.0)


def test_noise_rng_isolated_per_seed_and_repeatable():
    spec = _ref_spec()
    spec.robot.sensor_noise_std_m = 0.02
    from app.schemas.scenario import Pose2D

    pose = Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0)
    truth = [{"id": "O1", "x_m": 3.0, "y_m": 4.0, "radius_m": 0.35}]

    def sample(seed):
        s = SensorSystem(spec.robot, spec.world.fixed_timestep_s, seed)
        s.capture_observation(0, 0.0, pose, truth)
        return s.queue[0].obstacles[0].rel_x_m

    assert sample(1842) == sample(1842)  # same seed repeats
    assert sample(1842) != sample(9999)  # seed isolation


def test_world_client_cleanup_on_exception():
    from app.schemas.scenario import WorldSpec

    world = SimulationWorld(WorldSpec(width_m=8.0, height_m=6.0, duration_limit_s=5.0))
    cid = world.connect()
    assert cid >= 0
    world.disconnect()
    assert world.client_id is None
    world.disconnect()  # idempotent, must not raise


def test_reference_run_produces_real_telemetry_and_repeats():
    spec = _ref_spec()
    seen = set()
    for _ in range(2):
        runner = SimulationRunner(spec, PolicyConfig(), configurable_policy)
        frames, metrics, reasons = runner.run()
        assert len(frames) > 0
        assert frames[0].tick == 0
        assert all(f.clearance_m == f.clearance_m for f in frames)  # finite
        status, _ = evaluate_oracle(metrics, spec.oracle, reasons)
        seen.add((status, metrics.total_ticks, round(metrics.min_clearance_m, 4)))
    assert len(seen) == 1  # deterministic repeat
    assert next(iter(seen))[0] == "FAIL"


def _drive_sensor(sys, ticks, truth_fn, pose_xy=(4.0, 4.0)):
    from app.schemas.scenario import Pose2D

    pose = Pose2D(x_m=pose_xy[0], y_m=pose_xy[1], yaw_rad=0.0)
    delivered = None
    for k in range(ticks):
        sys.capture_observation(k, k * sys.dt, pose, truth_fn(k, sys.dt))
        delivered = sys.get_delivered_observation(k, k * sys.dt)
    return delivered


def test_velocity_tracks_moving_obstacle():
    spec = _ref_spec()
    sys = SensorSystem(spec.robot, spec.world.fixed_timestep_s, spec.seed)
    d = _drive_sensor(
        sys,
        40,
        lambda k, dt: [{"id": "O1", "x_m": 6.0, "y_m": 4.0 + 0.45 * k * dt, "radius_m": 0.35}],
    )
    assert d.tracks and d.tracks[0].confident is True
    assert abs(d.tracks[0].vx_mps) < 0.05
    assert abs(d.tracks[0].vy_mps - 0.45) < 0.08


def test_velocity_zero_for_static_obstacle():
    spec = _ref_spec()
    sys = SensorSystem(spec.robot, spec.world.fixed_timestep_s, spec.seed)
    d = _drive_sensor(sys, 40, lambda k, dt: [{"id": "S", "x_m": 6.0, "y_m": 2.0, "radius_m": 0.3}])
    assert d.tracks and d.tracks[0].confident is True
    assert abs(d.tracks[0].vx_mps) < 1e-9 and abs(d.tracks[0].vy_mps) < 1e-9


def test_single_sample_track_not_confident():
    spec = _ref_spec()
    sys = SensorSystem(spec.robot, spec.world.fixed_timestep_s, spec.seed)
    d = _drive_sensor(sys, 1, lambda k, dt: [{"id": "Q", "x_m": 3.0, "y_m": 4.0, "radius_m": 0.3}])
    assert d.tracks == [] or all(t.confident is False for t in d.tracks)
