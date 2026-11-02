"""Edge-branch tests: run metrics, oracle inconclusive paths, log oracle."""

from app.schemas.scenario import OracleSpec
from app.schemas.telemetry import (
    CommandTelemetry,
    EventRecord,
    Pose2D,
    RunMetrics,
    SensorTelemetry,
    TelemetryFrame,
)
from app.verification.log_oracle import evaluate_imported_track
from app.verification.metrics import compute_run_metrics
from app.verification.oracle import evaluate_oracle


def _frame(tick: int, clearance: float, events=None) -> TelemetryFrame:
    return TelemetryFrame(
        tick=tick,
        sim_time_s=tick / 60.0,
        robot=Pose2D(x_m=1.0, y_m=4.0, yaw_rad=0.0),
        obstacles=[],
        sensor=SensorTelemetry(
            sample_tick=tick, delivered_tick=tick, age_s=0.0, valid=True, observations=[]
        ),
        command=CommandTelemetry(linear_mps=0.5, angular_radps=0.0),
        clearance_m=clearance,
        events=events or [],
    )


def _event(type_: str, tick: int) -> EventRecord:
    return EventRecord(event_id=f"e{tick}", type=type_, tick=tick, sim_time_s=0.0, details={})


def test_compute_metrics_empty_and_full():
    empty = compute_run_metrics([])
    assert empty.total_ticks == 0 and empty.timeout_detected is True

    frames = [
        _frame(0, 1.0),
        _frame(60, 0.1, [_event("COLLISION", 60)]),
        _frame(120, 0.5, [_event("GOAL_REACHED", 120)]),
    ]
    metrics = compute_run_metrics(frames)
    assert metrics.total_ticks == 3
    assert metrics.min_clearance_m == 0.1
    assert metrics.collision_detected is True and metrics.goal_reached is True
    assert metrics.sim_duration_s == 2.0


def test_oracle_missing_telemetry_is_inconclusive():
    metrics = RunMetrics(
        total_ticks=0,
        sim_duration_s=0.0,
        min_clearance_m=0.0,
        goal_reached=False,
        collision_detected=False,
        stuck_detected=False,
        timeout_detected=False,
    )
    status, reasons = evaluate_oracle(metrics, OracleSpec(max_duration_s=30.0), [])
    assert status == "INCONCLUSIVE" and reasons == ["MISSING_TELEMETRY"]


def test_log_oracle_no_goal_and_single_frame_branches():
    from app.schemas.telemetry_import import ImportedFrame

    frames = [
        ImportedFrame(t_s=0.0, x_m=0.0, y_m=0.0, min_obstacle_distance_m=1.0),
        ImportedFrame(t_s=1.0, x_m=1.0, y_m=0.0, min_obstacle_distance_m=0.9),
    ]
    status, reasons, metrics = evaluate_imported_track(frames, None, 0.35, 0.25)
    assert status == "PASS" and reasons == []
    assert metrics.path_length_m == 1.0

    single = [ImportedFrame(t_s=0.0, x_m=0.0, y_m=0.0, min_obstacle_distance_m=1.0)]
    status, reasons, _ = evaluate_imported_track(single, None, 0.35, 0.25)
    assert status == "INCONCLUSIVE"
