"""Job execution service implementing simulation and verification workflows."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from app.config import settings
from app.db import get_db
from app.evidence.integrity import seal_package_hashes, verify_package_integrity
from app.evidence.recorder import (
    VERIFICATION_REQUIRED_FILES,
    save_run_artifacts,
    save_verification_artifacts,
)
from app.evidence.reporter import generate_verification_report
from app.policies.candidate_law import get_candidate_policy_fn
from app.policies.configurable import configurable_policy
from app.policies.local_adapter import SubprocessPolicy
from app.ai.adversarial import clamp_iterations, run_adversarial_rounds
from app.ai.adapter import get_ai_adapter
from app.schemas.battery import BatteryEntry, BatteryResult, is_near_miss, summarize
from app.schemas.stress import StressCell, StressTestResult, summarize_cells
from app.schemas.jobs import JobProgress, JobRecord
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner
from app.verification.holdout import evaluate_holdouts
from app.verification.oracle import evaluate_oracle
from app.verification.paired import (
    compute_policy_hash,
    compute_spec_hash,
    evaluate_paired_comparison,
)
from app.verification.regression import evaluate_regressions
from app.webhooks import notify


class JobExecutionService:
    def __init__(self):
        self.artifacts_root = settings.artifacts_path
        self.scenarios_root = Path(__file__).resolve().parent.parent.parent.parent / "scenarios"

    def execute_simulation_run(self, job: JobRecord) -> None:
        data = json.loads(job.payload_json)
        scenario = ScenarioSpec.model_validate(data["scenario"])
        policy = PolicyConfig.model_validate(data["policy"])
        plugin = SubprocessPolicy(data["local_policy"]) if data.get("local_policy") else None
        try:
            self._execute_single_run(
                scenario=scenario,
                policy=policy,
                run_id=job.result_id,
                job_id=job.job_id,
                created_at=job.created_at,
                policy_fn=plugin,
            )
        finally:
            if plugin is not None:
                plugin.close()

    def _execute_single_run(self, scenario, policy, run_id, job_id, created_at, policy_fn=None):
        """Run one scenario, persist run row + artifacts, return measured verdict."""
        # Single shared navigation law for baseline and candidate; only params differ.
        # A local user policy (İş 3B) replaces the law only when explicitly chosen.
        runner = SimulationRunner(scenario, policy, policy_fn or configurable_policy)
        frames, metrics, raw_reasons = runner.run()

        oracle_status, final_reasons = evaluate_oracle(metrics, scenario.oracle, raw_reasons)

        art_dir = save_run_artifacts(
            artifacts_root=self.artifacts_root,
            run_id=run_id,
            scenario=scenario,
            policy=policy,
            frames=frames,
            metrics=metrics,
            oracle_status=oracle_status,
            reason_codes=final_reasons,
        )

        now = datetime.now(timezone.utc).isoformat()
        scenario_hash = compute_spec_hash(scenario)
        policy_hash = compute_policy_hash(policy)

        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, job_id, scenario_hash, policy_hash,
                    oracle_status, reason_codes_json, metrics_json,
                    artifact_dir, created_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    job_id,
                    scenario_hash,
                    policy_hash,
                    oracle_status,
                    json.dumps(final_reasons),
                    metrics.model_dump_json(),
                    str(art_dir),
                    created_at,
                    now,
                ),
            )
            conn.commit()
        return oracle_status, final_reasons, metrics

    def execute_battery_run(self, job: JobRecord, progress_callback=None) -> None:
        """Run a whole scenario battery for one robot and store the report card."""
        data = json.loads(job.payload_json)
        policy = PolicyConfig.model_validate(data["policy"])
        battery_id = job.result_id
        items = data["scenarios"]  # [{scenario, title}] with robot already applied
        entries: list[BatteryEntry] = []
        total = len(items)

        for idx, item in enumerate(items):
            scenario = ScenarioSpec.model_validate(item["scenario"])
            if progress_callback:
                progress_callback(
                    JobProgress(
                        pct=round(idx / max(total, 1) * 100.0, 1),
                        current_step=idx + 1,
                        total_steps=total,
                        message=f"Running {scenario.id} ({idx + 1}/{total})",
                    )
                )
            run_id = f"run-{uuid.uuid4().hex[:12]}"
            plugin = SubprocessPolicy(data["local_policy"]) if data.get("local_policy") else None
            try:
                status_, reasons, metrics = self._execute_single_run(
                    scenario=scenario,
                    policy=policy,
                    run_id=run_id,
                    job_id=job.job_id,
                    created_at=job.created_at,
                    policy_fn=plugin,
                )
            finally:
                if plugin is not None:
                    plugin.close()
            entries.append(
                BatteryEntry(
                    scenario_id=scenario.id,
                    title=item.get("title", scenario.id),
                    run_id=run_id,
                    oracle_status=status_,
                    reason_codes=reasons,
                    metrics=metrics,
                    near_miss=is_near_miss(status_, reasons, metrics),
                )
            )

        if progress_callback:
            progress_callback(
                JobProgress(pct=100.0, current_step=total, total_steps=total, message="Done")
            )

        result = BatteryResult(
            battery_id=battery_id,
            robot_id=data["robot_id"],
            robot_label=data.get("robot_label", data["robot_id"]),
            policy_id=policy.id,
            entries=entries,
            summary=summarize(entries),
            created_at=job.created_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO battery_runs (battery_id, robot_id, result_json, created_at, "
                "workspace_id) VALUES (?, ?, ?, ?, ?)",
                (
                    battery_id,
                    result.robot_id,
                    result.model_dump_json(),
                    job.created_at,
                    data.get("workspace_id", "default"),
                ),
            )
            conn.commit()
        notify(
            "battery.completed",
            {
                "battery_id": battery_id,
                "robot_id": result.robot_id,
                "robot_label": result.robot_label,
                "summary": result.summary.model_dump(),
            },
        )

    def execute_stress_test(self, job: JobRecord, progress_callback=None) -> None:
        """Sensor stress grid: vary latency x noise on copies of one scenario.

        Each cell is an ordinary recorded run (same oracle, same law); the
        grid never relaxes thresholds — it only stresses the sensor model.
        """
        data = json.loads(job.payload_json)
        base = ScenarioSpec.model_validate(data["scenario"])
        policy = PolicyConfig.model_validate(data["policy"])
        latencies = [int(v) for v in data["latencies_ms"]]
        noises = [float(v) for v in data["noise_levels_m"]]
        cells: list[StressCell] = []
        total = len(latencies) * len(noises)
        idx = 0
        for latency in latencies:
            for noise in noises:
                idx += 1
                if progress_callback:
                    progress_callback(
                        JobProgress(
                            pct=round((idx - 1) / max(total, 1) * 100.0, 1),
                            current_step=idx,
                            total_steps=total,
                            message=f"Stress cell {idx}/{total}: {latency} ms, noise {noise} m",
                        )
                    )
                variant = base.model_copy(
                    update={
                        "robot": base.robot.model_copy(
                            update={"sensor_latency_ms": latency, "sensor_noise_std_m": noise}
                        )
                    }
                )
                variant = ScenarioSpec.model_validate(variant.model_dump())
                run_id = f"run-{uuid.uuid4().hex[:12]}"
                status_, reasons, metrics = self._execute_single_run(
                    scenario=variant,
                    policy=policy,
                    run_id=run_id,
                    job_id=job.job_id,
                    created_at=job.created_at,
                )
                cells.append(
                    StressCell(
                        latency_ms=latency,
                        noise_std_m=noise,
                        run_id=run_id,
                        oracle_status=status_,
                        reason_codes=reasons,
                        metrics=metrics,
                        near_miss=is_near_miss(status_, reasons, metrics),
                    )
                )
        if progress_callback:
            progress_callback(
                JobProgress(pct=100.0, current_step=total, total_steps=total, message="Done")
            )
        result = StressTestResult(
            stress_id=job.result_id,
            scenario_id=base.id,
            policy_id=policy.id,
            latencies_ms=latencies,
            noise_levels_m=noises,
            cells=cells,
            summary=summarize_cells(cells),
            created_at=job.created_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO stress_runs (stress_id, scenario_id, result_json, created_at, "
                "workspace_id) VALUES (?, ?, ?, ?, ?)",
                (
                    result.stress_id,
                    result.scenario_id,
                    result.model_dump_json(),
                    job.created_at,
                    data.get("workspace_id", "default"),
                ),
            )
            conn.commit()

    def execute_adversarial_test(self, job: JobRecord, progress_callback=None) -> None:
        """Bounded adversarial rounds: the AI proposes scenarios, each one is
        executed and judged by the ordinary oracle. The AI never decides."""
        data = json.loads(job.payload_json)
        policy = PolicyConfig.model_validate(data["policy"])
        max_iterations = clamp_iterations(
            data.get("max_iterations"), settings.RW_ADVERSARIAL_MAX_ITERATIONS
        )

        seed_summary = ""
        seed_run_id = data.get("seed_run_id")
        if seed_run_id:
            with get_db() as conn:
                row = conn.execute(
                    "SELECT oracle_status, reason_codes_json, metrics_json FROM runs "
                    "WHERE run_id = ?",
                    (seed_run_id,),
                ).fetchone()
            if row is not None:
                seed_summary = (
                    f"seed run {seed_run_id}: {row['oracle_status']} "
                    f"reasons={row['reason_codes_json']} metrics={row['metrics_json']}"
                )[:800]

        adapter = get_ai_adapter()

        def _execute(scenario):
            run_id = f"run-{uuid.uuid4().hex[:12]}"
            status_, reasons, metrics = self._execute_single_run(
                scenario=scenario,
                policy=policy,
                run_id=run_id,
                job_id=job.job_id,
                created_at=job.created_at,
            )
            return status_, reasons, metrics, run_id

        if progress_callback:
            progress_callback(
                JobProgress(
                    pct=5.0,
                    current_step=0,
                    total_steps=max_iterations,
                    message="Starting adversarial rounds",
                )
            )
        result = run_adversarial_rounds(
            adapter=adapter,
            policy=policy,
            max_iterations=max_iterations,
            execute=_execute,
            seed_failure_summary=seed_summary,
        )
        result.adversarial_id = job.result_id
        result.created_at = job.created_at
        result.completed_at = datetime.now(timezone.utc).isoformat()
        if progress_callback:
            progress_callback(
                JobProgress(
                    pct=100.0,
                    current_step=max_iterations,
                    total_steps=max_iterations,
                    message="Done",
                )
            )
        with get_db() as conn:
            conn.execute(
                "INSERT INTO adversarial_runs (adversarial_id, result_json, created_at, "
                "workspace_id) VALUES (?, ?, ?, ?)",
                (
                    result.adversarial_id,
                    result.model_dump_json(),
                    job.created_at,
                    data.get("workspace_id", "default"),
                ),
            )
            conn.commit()

    def execute_verification(self, job: JobRecord, progress_callback=None) -> None:
        data = json.loads(job.payload_json)
        baseline_run_id = data["baseline_run_id"]
        candidate_policy = PolicyConfig.model_validate(data["candidate_policy"])
        verification_id = job.result_id

        # 1. Load baseline run from DB and artifact
        baseline_run_dir = self.artifacts_root / "runs" / baseline_run_id
        scenario_file = baseline_run_dir / "scenario.json"
        metrics_file = baseline_run_dir / "metrics.json"

        with open(scenario_file, "r", encoding="utf-8") as f:
            scenario = ScenarioSpec.model_validate_json(f.read())
        with open(metrics_file, "r", encoding="utf-8") as f:
            json.load(f)  # validate artifact readability; metrics re-measured below

        gates = []

        # Gate 1: Reproduce Baseline Failure
        if progress_callback:
            progress_callback(
                JobProgress(
                    pct=15.0,
                    current_step=1,
                    total_steps=5,
                    message="Reproducing baseline failure",
                )
            )

        b_runner = SimulationRunner(scenario, PolicyConfig(), configurable_policy)
        b_frames, b_metrics, b_raw_reasons = b_runner.run()
        b_status, b_reasons = evaluate_oracle(b_metrics, scenario.oracle, b_raw_reasons)

        gate1_passed = b_status == "FAIL"
        gates.append(
            {
                "gate_id": "GATE_1_REPRODUCE",
                "name": "Baseline Failure Reproduction",
                "status": "PASS" if gate1_passed else "FAIL",
                "reason_codes": [] if gate1_passed else ["REPRODUCTION_FAILED"],
                "details": {"baseline_oracle_status": b_status, "reasons": b_reasons},
            }
        )

        # Gate 2: Paired Comparison
        if progress_callback:
            progress_callback(
                JobProgress(
                    pct=35.0,
                    current_step=2,
                    total_steps=5,
                    message="Evaluating paired comparison",
                )
            )

        c_runner = SimulationRunner(scenario, candidate_policy, get_candidate_policy_fn())
        c_frames, c_metrics, c_raw_reasons = c_runner.run()
        c_status, c_reasons = evaluate_oracle(c_metrics, scenario.oracle, c_raw_reasons)

        gate2_res = evaluate_paired_comparison(b_metrics, c_metrics, b_reasons, c_reasons)
        gates.append(gate2_res.model_dump())

        # Gate 3: Frozen 20 Holdouts
        if progress_callback:
            progress_callback(
                JobProgress(
                    pct=65.0,
                    current_step=3,
                    total_steps=5,
                    message="Evaluating 20 frozen holdouts",
                )
            )

        holdout_manifest = self.scenarios_root / "holdout" / "manifest.json"
        gate3_res = evaluate_holdouts(candidate_policy, holdout_manifest)
        gates.append(gate3_res.model_dump())

        # Gate 4: Critical Regressions
        if progress_callback:
            progress_callback(
                JobProgress(
                    pct=85.0,
                    current_step=4,
                    total_steps=5,
                    message="Evaluating critical regressions",
                )
            )

        regression_dir = self.scenarios_root / "regression"
        gate4_res = evaluate_regressions(candidate_policy, regression_dir)
        gates.append(gate4_res.model_dump())

        # Decide provisional verdict
        all_passed = all(g["status"] == "PASS" for g in gates)
        any_failed = any(g["status"] == "FAIL" for g in gates)

        if all_passed:
            provisional_verdict = "VERIFIED_IN_SIMULATION"
        elif any_failed:
            provisional_verdict = "REJECTED"
        else:
            provisional_verdict = "INCONCLUSIVE"

        # Gate 5: Evidence Sealing — provisional first, seal, then independently
        # re-verify the sealed bytes BEFORE publishing a VERIFIED verdict.
        if progress_callback:
            progress_callback(
                JobProgress(
                    pct=95.0,
                    current_step=5,
                    total_steps=5,
                    message="Sealing evidence package",
                )
            )

        manifest = {
            "schema_version": "1.0",
            "verification_id": verification_id,
            "baseline_run_id": baseline_run_id,
            "verdict": provisional_verdict,
            "gates_provisional": [g["gate_id"] for g in gates],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        report_md = generate_verification_report(
            verification_id=verification_id,
            baseline_run_id=baseline_run_id,
            verdict=provisional_verdict,
            gates=gates,
            manifest=manifest,
            holdout_summary=gate3_res.details,
            regression_summary=gate4_res.details,
        )

        art_dir = save_verification_artifacts(
            artifacts_root=self.artifacts_root,
            verification_id=verification_id,
            manifest=manifest,
            investigation={"hypothesis": "Observation latency mitigation via tuned deceleration"},
            comparison={
                "baseline": b_metrics.model_dump(),
                "candidate": c_metrics.model_dump(),
            },
            holdout_results=gate3_res.details,
            regression_results=gate4_res.details,
            report_content=report_md,
            candidate_frames=c_frames,
        )

        integrity_ok, integrity_errors = verify_package_integrity(
            art_dir, VERIFICATION_REQUIRED_FILES
        )
        if integrity_ok:
            final_verdict = provisional_verdict
            gates.append(
                {
                    "gate_id": "GATE_5_INTEGRITY",
                    "name": "Evidence Integrity and Sealing",
                    "status": "PASS",
                    "reason_codes": [],
                    "details": {"sealed_directory": str(art_dir)},
                }
            )
        else:
            # Sealed package is incomplete/tampered: never publish VERIFIED.
            final_verdict = "INCONCLUSIVE"
            gates.append(
                {
                    "gate_id": "GATE_5_INTEGRITY",
                    "name": "Evidence Integrity and Sealing",
                    "status": "FAIL",
                    "reason_codes": ["ARTIFACT_INTEGRITY_FAILURE"],
                    "details": {
                        "sealed_directory": str(art_dir),
                        "errors": integrity_errors,
                    },
                }
            )
            # Rewrite manifest + report with the final INCONCLUSIVE verdict and reseal.
            manifest["verdict"] = final_verdict
            manifest["integrity_errors"] = integrity_errors
            report_md = generate_verification_report(
                verification_id=verification_id,
                baseline_run_id=baseline_run_id,
                verdict=final_verdict,
                gates=gates,
                manifest=manifest,
                holdout_summary=gate3_res.details,
                regression_summary=gate4_res.details,
            )
            with open(art_dir / "manifest.json", "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
            with open(art_dir / "report.md", "w", encoding="utf-8") as f:
                f.write(report_md)
            seal_package_hashes(art_dir)

        now = datetime.now(timezone.utc).isoformat()
        with get_db() as conn:
            conn.execute(
                """
                INSERT INTO verifications (
                    verification_id, job_id, baseline_run_id,
                    candidate_policy_json, verdict, gates_json,
                    artifact_dir, created_at, completed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    verification_id,
                    job.job_id,
                    baseline_run_id,
                    candidate_policy.model_dump_json(),
                    final_verdict,
                    json.dumps(gates),
                    str(art_dir),
                    job.created_at,
                    now,
                ),
            )
            conn.commit()
