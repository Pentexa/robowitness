"""Generate FROZEN holdout set v2 (fresh seeds) — deterministic, validated.

Disclosure: holdout v1 (scenarios/holdout/manifest_v1_dev.json) was used during
dev exploration to tune candidate parameters. Per the blueprint, a rerun on v1
cannot be described as untouched holdout verification. This script therefore
creates a NEWLY VERSIONED frozen set (v2) from the same recipe family with
fresh IDs/seeds. The final candidate is evaluated on v2 WITHOUT further tuning.

Recipe v2 (mirrors v1 distribution):
  - warehouse 12x8m, 30s limit, 1/60s tick
  - robot start (1,4,0) -> goal (11,4), body r=0.25, range 4.0m
  - one ping-pong obstacle: x in [5.0,7.0], y-span >= 3.0m within [1.0,7.0],
    radius 0.30..0.38m, speed 0.36..0.50 m/s
  - sensor latency {100..400}ms, noise {0.0,0.01,0.02}
  - oracle: collision_free, min_clearance 0.25m, must reach goal, 30s, stuck 3s

Every generated case is validated by ScenarioSpec (rejects overlaps/out-of-bounds).
Output: scenarios/holdout/manifest.json (frozen eval set).
"""
import json
import random
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.schemas.scenario import ScenarioSpec

HOLDOUT_DIR = ROOT_DIR / "scenarios" / "holdout"
LATENCIES = [100, 150, 200, 250, 300, 350, 400]
NOISES = [0.0, 0.01, 0.02]


def parse_args(argv):
    """generate_holdout_v2.py [out_name id_prefix seed_start recipe recipe_seed archive_name]"""
    return {
        "out": argv[1] if len(argv) > 1 else "manifest.json",
        "prefix": argv[2] if len(argv) > 2 else "RW-HLD2",
        "seed_start": int(argv[3]) if len(argv) > 3 else 3001,
        "recipe": argv[4] if len(argv) > 4 else "frozen_holdout_v2",
        "recipe_seed": int(argv[5]) if len(argv) > 5 else 20261030,
        "archive": argv[6] if len(argv) > 6 else "manifest_v1_dev.json",
    }


def generate_case(rng: random.Random, idx: int, prefix: str, seed_start: int) -> dict:
    seed = seed_start + idx - 1
    case_id = "%s-%03d" % (prefix, idx)
    obs_x = round(rng.uniform(5.0, 7.0), 2)
    y_a = round(rng.uniform(1.0, 7.0), 2)
    # Ensure y-span >= 3.0m staying inside [1.0, 7.0] with radius margin 0.38.
    y_b = round(rng.uniform(1.0, 7.0), 2)
    if abs(y_a - y_b) < 3.0:
        y_b = round(7.0 if y_a < 4.0 else 1.0, 2)
    radius = round(rng.uniform(0.30, 0.38), 2)
    speed = round(rng.uniform(0.36, 0.50), 2)
    latency = rng.choice(LATENCIES)
    noise = rng.choice(NOISES)
    return {
        "schema_version": "1.0",
        "id": case_id,
        "kind": "dynamic_obstacle",
        "seed": seed,
        "world": {
            "type": "warehouse",
            "width_m": 12.0,
            "height_m": 8.0,
            "duration_limit_s": 30.0,
            "fixed_timestep_s": 0.016666666666666666,
        },
        "robot": {
            "kind": "differential_drive",
            "start": {"x_m": 1.0, "y_m": 4.0, "yaw_rad": 0.0},
            "goal": {"x_m": 11.0, "y_m": 4.0},
            "goal_radius_m": 0.35,
            "body_radius_m": 0.25,
            "wheel_base_m": 0.42,
            "wheel_radius_m": 0.09,
            "sensor_range_m": 4.0,
            "sensor_latency_ms": latency,
            "sensor_noise_std_m": noise,
        },
        "obstacles": [
            {
                "id": "O1",
                "shape": "circle",
                "radius_m": radius,
                "motion": "ping_pong",
                "start": {"x_m": obs_x, "y_m": y_a},
                "end": {"x_m": obs_x, "y_m": y_b},
                "speed_mps": speed,
            }
        ],
        "oracle": {
            "collision_free": True,
            "min_clearance_m": 0.25,
            "must_reach_goal": True,
            "max_duration_s": 30.0,
            "max_stuck_duration_s": 3.0,
        },
    }


def main() -> int:
    args = parse_args(sys.argv)
    rng = random.Random(args["recipe_seed"])  # frozen recipe seed
    current = HOLDOUT_DIR / args["out"]
    if current.exists() and current.name == "manifest.json":
        archive = HOLDOUT_DIR / args["archive"]
        if not archive.exists():
            shutil.copy2(current, archive)
            print(f"Archived previous set -> {archive.name} (byte-exact copy)")

    scenarios = []
    attempts = 0
    idx = 1
    while len(scenarios) < 20 and attempts < 500:
        attempts += 1
        case = generate_case(rng, idx, args["prefix"], args["seed_start"])
        try:
            ScenarioSpec.model_validate(case)
        except Exception as e:
            print(f"  regenerate idx={idx}: {e}")
            continue
        scenarios.append(case)
        idx += 1

    if len(scenarios) != 20:
        print(f"[FAIL] only generated {len(scenarios)}/20 valid cases")
        return 1

    ids = [s["id"] for s in scenarios]
    seeds = [s["seed"] for s in scenarios]
    assert len(set(ids)) == 20 and len(set(seeds)) == 20

    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "recipe": args["recipe"],
        "recipe_seed": args["recipe_seed"],
        "total_scenarios": 20,
        "note": "Frozen final-evaluation set.",
        "scenarios": scenarios,
    }
    with open(current, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"Wrote frozen v2 set: 20 cases -> {current}")
    for s in scenarios:
        o = s["obstacles"][0]
        print(f"  {s['id']} seed={s['seed']} lat={s['robot']['sensor_latency_ms']}ms "
              f"noise={s['robot']['sensor_noise_std_m']} x={o['start']['x_m']} "
              f"y={o['start']['y_m']}->{o['end']['y_m']} r={o['radius_m']} v={o['speed_mps']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
