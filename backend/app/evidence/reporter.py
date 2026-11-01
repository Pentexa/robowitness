"""Audit-grade human-readable verification report generator."""

from typing import Any, Dict


def generate_verification_report(
    verification_id: str,
    baseline_run_id: str,
    verdict: str,
    gates: list,
    manifest: Dict[str, Any],
    holdout_summary: Dict[str, Any],
    regression_summary: Dict[str, Any],
) -> str:
    lines = [
        "# RoboWitness Independent Verification Report",
        "",
        f"**Verification ID:** `{verification_id}`  ",
        f"**Baseline Run ID:** `{baseline_run_id}`  ",
        f"**Final Verdict:** **`{verdict}`**  ",
        "",
        "> **Notice:** Software-only simulation verification. "
        "No physical-world safety certification is claimed or implied.",
        "",
        "## 1. Executive Summary",
        "RoboWitness executed an independent verification sequence to evaluate whether "
        "a candidate controller parameter fix survives rigorous simulation gates "
        "without regressions or holdout overfitting.",
        "",
        "## 2. Gate Verification Results",
        "",
        "| Gate | Name | Status | Details |",
        "|---|---|---|---|",
    ]

    for g in gates:
        g_id = g.get("gate_id", "")
        name = g.get("name", "")
        status = g.get("status", "")
        reasons = ", ".join(g.get("reason_codes", [])) or "None"
        lines.append(f"| {g_id} | {name} | **{status}** | {reasons} |")

    lines.extend(
        [
            "",
            "## 3. Holdout Evaluation (Gate 3)",
            f"- **Total Holdout Cases:** {holdout_summary.get('total_cases', 20)}",
            f"- **Passed Cases:** {holdout_summary.get('passed_cases', 0)}",
            f"- **Failed Cases:** {holdout_summary.get('failed_cases', 0)}",
            "",
            "## 4. Critical Regressions (Gate 4)",
            f"- **Total Regression Cases:** {regression_summary.get('total_cases', 3)}",
            f"- **Passed Cases:** {regression_summary.get('passed_cases', 0)}",
            "",
            "## 5. Cryptographic Evidence Sealing",
            "All artifacts in this package are sealed with SHA-256 hashes listed in `hashes.json`.",
            "To independently verify integrity, run:",
            "```bash",
            f"python scripts/verify_evidence.py artifacts/verifications/{verification_id}",
            "```",
        ]
    )

    return "\n".join(lines)
