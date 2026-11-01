"""Job execution service implementing simulation and verification workflows."""

import json
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
from app.policies.configurable import configurable_policy
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


class JobExecutionService:
    def __init__(self):
        self.artifacts_root = settings.artifacts_path
        self.scenarios_root = Path(__file__).resolve().parent.parent.parent.parent / "scenarios"

    def execute_simulation_run(self, job: JobRecord) -> None:
        data = json.loads(job.payload_json)
        scenario = ScenarioSpec.model_validate(data["scenario"])
        policy = PolicyConfig.model_validate(data["policy"])
        run_id = job.result_id

        # Single shared navigation law for baseline and candidate; only params differ.
        runner = SimulationRunner(scenario, policy, configurable_policy)
        frames, metrics, raw_reasons = runner.run()

        oracle_status, final_reasons = evaluate_oracle(metrics, scenario.oracle, raw_reasons)

        # Save evidence artifacts
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
                    job.job_id,
                    scenario_hash,
                    policy_hash,
                    oracle_status,
                    json.dumps(final_reasons),
                    metrics.model_dump_json(),
                    str(art_dir),
                    job.created_at,
                    now,
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

        c_runner = SimulationRunner(scenario, candidate_policy, configurable_policy)
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
