"""Adversarial scenario rounds: AI proposes, the oracle disposes.

Muse Spark (or the offline reference adapter) iteratively generates
challenging scenarios informed by measured failures from previous rounds.
Strict limits: at most MAX_ITERATIONS rounds (config
RW_ADVERSARIAL_MAX_ITERATIONS, hard cap 10), one generation call per round,
duplicate scenarios are not re-run, and an UNAVAILABLE adapter stops the
loop honestly. The AI never judges: every executed scenario is run through
the ordinary simulator + oracle, and its recorded run is the evidence.
"""

from typing import Callable, List, Optional
from app.schemas.adversarial import AdversarialResult, AdversarialRound
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.verification.paired import compute_spec_hash

HARD_MAX_ITERATIONS = 10

ExecuteFn = Callable[[ScenarioSpec], tuple[str, List[str], object, str]]


def _failure_digest(rounds: List[AdversarialRound]) -> str:
    parts = []
    for r in rounds:
        if r.executed and r.oracle_status:
            parts.append(
                f"round {r.iteration}: scenario {r.scenario_id} -> {r.oracle_status} "
                f"reasons={','.join(r.reason_codes) or 'none'} "
                f"min_clearance_m={r.min_clearance_m}"
            )
    return "; ".join(parts) if parts else "no executed rounds yet"


def run_adversarial_rounds(
    adapter,
    policy: PolicyConfig,
    max_iterations: int,
    execute: ExecuteFn,
    seed_failure_summary: str = "",
) -> AdversarialResult:
    """Run the bounded generation loop. `execute` runs one scenario and
    returns (oracle_status, reason_codes, metrics, run_id)."""
    rounds: List[AdversarialRound] = []
    seen_hashes: set[str] = set()
    total_tokens = 0
    stopped_reason = "iteration_limit"

    for iteration in range(1, max_iterations + 1):
        digest = _failure_digest(rounds)
        prompt = (
            "Generate one challenging warehouse ScenarioSpec that stresses a "
            "differential-drive robot policy relying on delayed, noisy obstacle "
            "sensing. Avoid repeating earlier scenarios. "
            f"Measured outcomes so far: {digest}."
        )
        if seed_failure_summary:
            prompt += f" Known failure context: {seed_failure_summary}."
        scenario, provenance = adapter.generate_scenario(prompt)
        usage = getattr(adapter, "last_usage", {}) or {}
        total_tokens += int(usage.get("total_tokens", 0) or 0)

        if scenario is None:
            rounds.append(
                AdversarialRound(
                    iteration=iteration,
                    provenance=provenance,
                    executed=False,
                    note="adapter_unavailable",
                )
            )
            stopped_reason = "adapter_unavailable"
            break

        spec_hash = compute_spec_hash(scenario)
        if spec_hash in seen_hashes:
            rounds.append(
                AdversarialRound(
                    iteration=iteration,
                    scenario_id=scenario.id,
                    provenance=provenance,
                    executed=False,
                    note="duplicate_scenario_not_rerun",
                )
            )
            continue
        seen_hashes.add(spec_hash)

        status_, reasons, metrics, run_id = execute(scenario)
        rounds.append(
            AdversarialRound(
                iteration=iteration,
                scenario_id=scenario.id,
                provenance=provenance,
                executed=True,
                run_id=run_id,
                oracle_status=status_,
                reason_codes=reasons,
                min_clearance_m=getattr(metrics, "min_clearance_m", None),
                note="oracle_judged",
            )
        )

    executed = [r for r in rounds if r.executed]
    return AdversarialResult(
        adversarial_id="",  # filled by the job service
        policy_id=policy.id,
        max_iterations=max_iterations,
        rounds=rounds,
        executed_count=len(executed),
        fail_count=sum(1 for r in executed if r.oracle_status == "FAIL"),
        pass_count=sum(1 for r in executed if r.oracle_status == "PASS"),
        total_tokens_used=total_tokens,
        stopped_reason=stopped_reason,
        created_at="",  # filled by the job service
    )


def clamp_iterations(requested: Optional[int], configured: int) -> int:
    want = requested if requested is not None else configured
    return max(1, min(int(want), HARD_MAX_ITERATIONS))
