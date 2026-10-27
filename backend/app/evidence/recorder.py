"""Atomic evidence persistence for runs and verifications."""
import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from app.evidence.integrity import seal_package_hashes
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.telemetry import RunMetrics, TelemetryFrame

RUN_REQUIRED_FILES = [
    "scenario.json",
    "policy.json",
    "manifest.json",
    "telemetry.jsonl",
    "metrics.json",
    "events.jsonl",
]

VERIFICATION_REQUIRED_FILES = [
    "manifest.json",
    "investigation.json",
    "comparison.json",
    "holdout_results.json",
    "regression_results.json",
    "report.md",
]

def save_run_artifacts(
    artifacts_root: Path,
    run_id: str,
    scenario: ScenarioSpec,
    policy: PolicyConfig,
    frames: List[TelemetryFrame],
    metrics: RunMetrics,
    oracle_status: str,
    reason_codes: List[str],
) -> Path:
    final_dir = artifacts_root / "runs" / run_id
    final_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=artifacts_root) as tmp:
        tmp_dir = Path(tmp)

        # 1. scenario.json
        with open(tmp_dir / "scenario.json", "w", encoding="utf-8") as f:
            f.write(scenario.model_dump_json(indent=2))

        # 2. policy.json
        with open(tmp_dir / "policy.json", "w", encoding="utf-8") as f:
            f.write(policy.model_dump_json(indent=2))

        # 3. telemetry.jsonl and events.jsonl
        with open(tmp_dir / "telemetry.jsonl", "w", encoding="utf-8") as tf, open(tmp_dir / "events.jsonl", "w", encoding="utf-8") as ef:
            for frame in frames:
                tf.write(frame.model_dump_json() + "\n")
                for evt in frame.events:
                    ef.write(evt.model_dump_json() + "\n")

        # 4. metrics.json
        with open(tmp_dir / "metrics.json", "w", encoding="utf-8") as f:
            f.write(metrics.model_dump_json(indent=2))

        # 5. manifest.json
        manifest = {
            "schema_version": "1.0",
            "run_id": run_id,
            "scenario_id": scenario.id,
            "seed": scenario.seed,
            "oracle_status": oracle_status,
            "reason_codes": reason_codes,
            "total_frames": len(frames),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(tmp_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        # 6. Seal package hashes
        seal_package_hashes(tmp_dir)

        # Atomic copy into final_dir
        for p in tmp_dir.glob("*"):
            if p.is_file():
                shutil.copy2(p, final_dir / p.name)

    return final_dir

def save_verification_artifacts(
    artifacts_root: Path,
    verification_id: str,
    manifest: Dict[str, Any],
    investigation: Dict[str, Any],
    comparison: Dict[str, Any],
    holdout_results: Dict[str, Any],
    regression_results: Dict[str, Any],
    report_content: str,
) -> Path:
    final_dir = artifacts_root / "verifications" / verification_id
    final_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=artifacts_root) as tmp:
        tmp_dir = Path(tmp)

        with open(tmp_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        with open(tmp_dir / "investigation.json", "w", encoding="utf-8") as f:
            json.dump(investigation, f, indent=2)

        with open(tmp_dir / "comparison.json", "w", encoding="utf-8") as f:
            json.dump(comparison, f, indent=2)

        with open(tmp_dir / "holdout_results.json", "w", encoding="utf-8") as f:
            json.dump(holdout_results, f, indent=2)

        with open(tmp_dir / "regression_results.json", "w", encoding="utf-8") as f:
            json.dump(regression_results, f, indent=2)

        with open(tmp_dir / "report.md", "w", encoding="utf-8") as f:
            f.write(report_content)

        seal_package_hashes(tmp_dir)

        for p in tmp_dir.glob("*"):
            if p.is_file():
                shutil.copy2(p, final_dir / p.name)

    return final_dir
