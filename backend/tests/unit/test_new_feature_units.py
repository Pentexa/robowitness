"""Unit tests for the five-feature round: inspector, adversarial, HTML report, stress."""

import io
import json
import zipfile
from pathlib import Path

from app.ai.adversarial import clamp_iterations, run_adversarial_rounds
from app.evidence.html_report import generate_verification_html
from app.evidence.inspector import inspect_evidence_zip
from app.evidence.integrity import seal_package_hashes
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.stress import StressCell, summarize_cells
from app.schemas.telemetry import RunMetrics


def _metrics(min_clearance=0.1):
    return RunMetrics(
        total_ticks=100,
        sim_duration_s=1.6,
        min_clearance_m=min_clearance,
        goal_reached=False,
        collision_detected=True,
        stuck_detected=False,
        timeout_detected=False,
    )


def _zip_of(directory: Path) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(directory.glob("*")):
            if path.is_file():
                zf.write(path, arcname=path.name)
    return buffer.getvalue()


def _make_run_package(tmp_path: Path) -> Path:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    for name in (
        "scenario.json",
        "policy.json",
        "telemetry.jsonl",
        "metrics.json",
        "events.jsonl",
    ):
        (pkg / name).write_text("{}", encoding="utf-8")
    (pkg / "manifest.json").write_text(
        json.dumps({"run_id": "run-test", "oracle_status": "FAIL"}), encoding="utf-8"
    )
    seal_package_hashes(pkg)
    return pkg


# ---------------------------------------------------------------- inspector


def test_inspector_accepts_valid_run_package(tmp_path):
    report = inspect_evidence_zip(_zip_of(_make_run_package(tmp_path)))
    assert report.ok, report.errors
    assert report.package_type == "run"
    assert report.package_id == "run-test"
    assert report.oracle_status == "FAIL"
    assert all(f.status in ("OK",) or f.name == "hashes.json" for f in report.files)


def test_inspector_detects_tampered_file(tmp_path):
    pkg = _make_run_package(tmp_path)
    (pkg / "metrics.json").write_text('{"tampered": true}', encoding="utf-8")
    report = inspect_evidence_zip(_zip_of(pkg))
    assert not report.ok
    assert any("TAMPERED" in e for e in report.errors)
    tampered = next(f for f in report.files if f.name == "metrics.json")
    assert tampered.status == "MISMATCH"


def test_inspector_detects_missing_required_file(tmp_path):
    pkg = _make_run_package(tmp_path)
    (pkg / "telemetry.jsonl").unlink()
    report = inspect_evidence_zip(_zip_of(pkg))
    assert not report.ok
    assert any("MISSING_MEMBER" in e for e in report.errors)
    missing = next(f for f in report.files if f.name == "telemetry.jsonl")
    assert missing.status == "MISSING"


def test_inspector_rejects_zip_slip_member(tmp_path):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("../evil.txt", "x")
        zf.writestr("manifest.json", json.dumps({"run_id": "run-x"}))
    report = inspect_evidence_zip(buffer.getvalue())
    assert not report.ok
    assert any("UNSAFE_MEMBER_NAME" in e for e in report.errors)


def test_inspector_rejects_non_zip_and_oversize_claims():
    assert not inspect_evidence_zip(b"not a zip").ok
    report = inspect_evidence_zip(b"not a zip")
    assert "NOT_A_ZIP_FILE" in report.errors


# -------------------------------------------------------------- adversarial


class _FakeAdapter:
    def __init__(self, specs):
        self._specs = list(specs)
        self.last_usage = {"total_tokens": 42}

    def generate_scenario(self, prompt):
        if not self._specs:
            return None, "UNAVAILABLE"
        return self._specs.pop(0), "LIVE_META"


def _scenario(sid: str, seed: int) -> ScenarioSpec:
    return ScenarioSpec.model_validate(
        {
            "id": sid,
            "kind": "dynamic_obstacle",
            "seed": seed,
            "world": {"width_m": 12.0, "height_m": 8.0, "duration_limit_s": 30.0},
            "robot": {
                "start": {"x_m": 1.0, "y_m": 4.0, "yaw_rad": 0.0},
                "goal": {"x_m": 11.0, "y_m": 4.0},
                "goal_radius_m": 0.35,
                "body_radius_m": 0.25,
                "sensor_latency_ms": 300,
                "sensor_noise_std_m": 0.0,
            },
            "obstacles": [
                {
                    "id": "O1",
                    "radius_m": 0.35,
                    "motion": "ping_pong",
                    "start": {"x_m": 6.0, "y_m": 1.0},
                    "end": {"x_m": 6.0, "y_m": 7.0},
                    "speed_mps": 0.4,
                }
            ],
            "oracle": {"max_duration_s": 30.0},
        }
    )


def test_adversarial_executes_and_judges_each_round():
    adapter = _FakeAdapter([_scenario("RW-ADV-1", 1), _scenario("RW-ADV-2", 2)])
    executed = []

    def fake_execute(spec):
        executed.append(spec.id)
        return "FAIL", ["COLLISION"], _metrics(0.0), f"run-{spec.id}"

    result = run_adversarial_rounds(adapter, PolicyConfig(), 2, fake_execute)
    assert result.executed_count == 2
    assert result.fail_count == 2
    assert result.total_tokens_used == 84
    assert result.stopped_reason == "iteration_limit"
    assert executed == ["RW-ADV-1", "RW-ADV-2"]


def test_adversarial_never_reruns_duplicate_scenario():
    spec = _scenario("RW-ADV-1", 7)
    adapter = _FakeAdapter([spec, spec, spec])
    calls = []

    def fake_execute(s):
        calls.append(s.id)
        return "PASS", [], _metrics(0.5), "run-1"

    result = run_adversarial_rounds(adapter, PolicyConfig(), 3, fake_execute)
    assert result.executed_count == 1
    assert calls == ["RW-ADV-1"]
    assert [r.note for r in result.rounds].count("duplicate_scenario_not_rerun") == 2


def test_adversarial_stops_honestly_when_adapter_unavailable():
    adapter = _FakeAdapter([])
    result = run_adversarial_rounds(adapter, PolicyConfig(), 5, lambda s: None)
    assert result.executed_count == 0
    assert result.stopped_reason == "adapter_unavailable"


def test_clamp_iterations_bounds():
    assert clamp_iterations(None, 5) == 5
    assert clamp_iterations(99, 5) == 10
    assert clamp_iterations(0, 5) == 1


# -------------------------------------------------------------- html report


def test_html_report_escapes_and_contains_measured_facts(tmp_path):
    art = tmp_path / "verifications" / "verif-test"
    art.mkdir(parents=True)
    doc = generate_verification_html(
        verification_id="verif-test",
        verdict="REJECTED",
        baseline_run_id="run-1",
        candidate_policy={"id": "cand-<script>alert(1)</script>", "max_speed_mps": 0.6},
        gates=[
            {
                "gate_id": "GATE_1_REPRODUCE",
                "name": "Baseline <Failure>",
                "status": "PASS",
                "reason_codes": [],
            }
        ],
        created_at="2026-11-04T00:00:00+00:00",
        artifact_dir=art,
    )
    assert "<script>alert(1)</script>" not in doc
    assert "&lt;script&gt;" in doc
    assert "REJECTED" in doc
    assert "GATE_1_REPRODUCE" in doc
    assert "No sealed telemetry available" in doc  # honest about missing chart data
    assert "<!DOCTYPE html>" in doc


# -------------------------------------------------------------------- stress


def test_stress_summary_counts_cells():
    cells = [
        StressCell(
            latency_ms=0,
            noise_std_m=0.0,
            run_id="r1",
            oracle_status="PASS",
            metrics=_metrics(0.4),
        ),
        StressCell(
            latency_ms=300,
            noise_std_m=0.0,
            run_id="r2",
            oracle_status="FAIL",
            metrics=_metrics(0.0),
        ),
        StressCell(
            latency_ms=300,
            noise_std_m=0.05,
            run_id="r3",
            oracle_status="FAIL",
            metrics=_metrics(0.1),
            near_miss=True,
        ),
    ]
    summary = summarize_cells(cells)
    assert (summary.total, summary.passed, summary.failed) == (3, 1, 2)
    assert summary.near_misses == 1
    assert summary.worst_clearance_m == 0.0
