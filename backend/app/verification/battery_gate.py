"""CI gate for battery results: pass/fail decision with explicit thresholds."""

from app.schemas.battery import BatteryResult


def evaluate_battery_gate(
    result: BatteryResult,
    min_pass_rate: float = 1.0,
    max_collisions: int = 0,
    max_near_misses: int | None = None,
) -> dict:
    s = result.summary
    pass_rate = (s.passed / s.total) if s.total else 0.0
    reasons: list[str] = []
    if pass_rate < min_pass_rate:
        reasons.append(
            f"pass rate {pass_rate:.2f} below required {min_pass_rate:.2f} ({s.passed}/{s.total})"
        )
    if s.collisions > max_collisions:
        reasons.append(f"collisions {s.collisions} above allowed {max_collisions}")
    if max_near_misses is not None and s.near_misses > max_near_misses:
        reasons.append(f"near misses {s.near_misses} above allowed {max_near_misses}")
    return {
        "passed": len(reasons) == 0,
        "pass_rate": round(pass_rate, 4),
        "reasons": reasons,
    }
