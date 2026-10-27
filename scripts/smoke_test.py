"""Smoke test script for verifying RoboWitness environment, imports, and schemas."""
import json
import sys
from pathlib import Path

# Add backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

def main():
    print("[1/3] Checking core Python modules...")
    try:
        import pydantic
        import fastapi
        print(f"  - Pydantic version: {pydantic.__version__}")
        print(f"  - FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        print(f"  [FAIL] Missing backend dependency: {e}")
        return 1

    print("[2/3] Validating canonical reference scenario fixture...")
    ref_path = ROOT_DIR / "scenarios" / "reference" / "moving_obstacle_latency.json"
    if not ref_path.exists():
        print(f"  [FAIL] Reference scenario missing at {ref_path}")
        return 1

    with open(ref_path, "r", encoding="utf-8") as f:
        spec_data = json.load(f)

    from app.schemas.scenario import ScenarioSpec
    try:
        spec = ScenarioSpec.model_validate(spec_data)
        print(f"  - Validated ScenarioSpec: {spec.id} (seed={spec.seed}, duration={spec.world.duration_limit_s}s)")
    except Exception as e:
        print(f"  [FAIL] Schema validation error: {e}")
        return 1

    print("[3/3] Validating 20-case holdout manifest...")
    holdout_path = ROOT_DIR / "scenarios" / "holdout" / "manifest.json"
    if not holdout_path.exists():
        print(f"  [FAIL] Holdout manifest missing at {holdout_path}")
        return 1

    with open(holdout_path, "r", encoding="utf-8") as f:
        holdout_data = json.load(f)

    scenarios = holdout_data.get("scenarios", [])
    if len(scenarios) != 20:
        print(f"  [FAIL] Expected 20 holdouts, got {len(scenarios)}")
        return 1

    ids = set()
    for item in scenarios:
        s = ScenarioSpec.model_validate(item)
        if s.id in ids:
            print(f"  [FAIL] Duplicate holdout id: {s.id}")
            return 1
        ids.add(s.id)

    print(f"  - All 20 unique holdout scenarios successfully validated.")
    print("ALL SMOKE TESTS PASSED.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
