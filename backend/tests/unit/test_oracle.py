"""Oracle verdict unit tests: real FAIL, boundary, clean PASS, INCONCLUSIVE."""

from app.schemas.scenario import OracleSpec
from app.schemas.telemetry import RunMetrics
from app.verification.oracle import evaluate_oracle


def _oracle() -> OracleSpec:
    return OracleSpec(
        collision_free=True,
        min_clearance_m=0.25,
        must_reach_goal=True,
        max_duration_s=30.0,
        max_stuck_duration_s=3.0,
    )


def _metrics(**kw) -> RunMetrics:
    base = dict(
        total_ticks=359,
        sim_duration_s=5.98,
        min_clearance_m=0.0016,
        goal_reached=False,
        collision_detected=True,
        stuck_detected=False,
        timeout_detected=False,
    )
    base.update(kw)
    return RunMetrics(**base)


def test_real_contact_yields_fail_with_collision():
    status, reasons = evaluate_oracle(_metrics(), _oracle(), ["COLLISION"])
    assert status == "FAIL"
    assert "COLLISION" in reasons
    assert "MIN_CLEARANCE_VIOLATION" in reasons  # 0.0016 < 0.25


def test_clearance_boundary_below_fails():
    m = _metrics(collision_detected=False, min_clearance_m=0.2499, goal_reached=True)
    status, reasons = evaluate_oracle(m, _oracle(), ["MIN_CLEARANCE_VIOLATION"])
    assert status == "FAIL"
    assert reasons == ["MIN_CLEARANCE_VIOLATION"]


def test_clearance_boundary_exact_passes():
    m = _metrics(collision_detected=False, min_clearance_m=0.25, goal_reached=True)
    status, reasons = evaluate_oracle(m, _oracle(), [])
    assert status == "PASS"
    assert reasons == []


def test_clean_run_passes():
    m = _metrics(collision_detected=False, min_clearance_m=0.7575, goal_reached=True)
    status, reasons = evaluate_oracle(m, _oracle(), [])
    assert status == "PASS"
    assert reasons == []


def test_goal_after_collision_still_fails():
    m = _metrics(min_clearance_m=0.0, goal_reached=True)
    status, reasons = evaluate_oracle(m, _oracle(), ["COLLISION"])
    assert status == "FAIL"
    assert "COLLISION" in reasons


def test_empty_telemetry_is_inconclusive():
    m = RunMetrics(
        total_ticks=0,
        sim_duration_s=0.0,
        min_clearance_m=0.0,
        goal_reached=False,
        collision_detected=False,
        stuck_detected=False,
        timeout_detected=False,
    )
    status, reasons = evaluate_oracle(m, _oracle(), [])
    assert status == "INCONCLUSIVE"
    assert "MISSING_TELEMETRY" in reasons


def test_stuck_and_timeout_surface_as_fail_reasons():
    m = _metrics(
        collision_detected=False,
        min_clearance_m=0.5,
        goal_reached=False,
        stuck_detected=True,
        timeout_detected=True,
    )
    status, reasons = evaluate_oracle(m, _oracle(), ["STUCK", "TIMEOUT"])
    assert status == "FAIL"
    assert "GOAL_NOT_REACHED" in reasons
    assert "TIMEOUT" in reasons
