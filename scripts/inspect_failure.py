"""Inspect a failing holdout case to ground the controller fix in measured data."""
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner
from app.verification.oracle import evaluate_oracle

C = PolicyConfig(id="candidate-final-v1", max_speed_mps=0.60, safe_distance_m=1.00,
                 reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.00)

manifest = json.load(open(ROOT_DIR / "scenarios" / "holdout" / "manifest.json"))
by_id = {s["id"]: s for s in manifest["scenarios"]}

for case_id in ("RW-HLD2-006", "RW-HLD2-017", "RW-HLD2-004"):
    spec = ScenarioSpec.model_validate(by_id[case_id])
    o = spec.obstacles[0]
    print(f"=== {case_id} lat={spec.robot.sensor_latency_ms}ms noise={spec.robot.sensor_noise_std_m} "
          f"obs x={o.start.x_m} y={o.start.y_m}->{o.end.y_m} r={o.radius_m} v={o.speed_mps}")
    frames, metrics, reasons = SimulationRunner(spec, C, configurable_policy).run()
    status, final = evaluate_oracle(metrics, spec.oracle, reasons)
    print(f"  {status} {final} ticks={len(frames)} min_clear={metrics.min_clearance_m}")
    for f in frames:
        for e in f.events:
            if e.type in ("COLLISION", "GOAL_REACHED", "STUCK", "TIMEOUT"):
                obs = f.obstacles[0]
                print(f"    tick={e.tick} ev={e.type} robot=({f.robot.x_m:.2f},{f.robot.y_m:.2f}) "
                      f"obs=({obs.x_m:.2f},{obs.y_m:.2f}) cmd=({f.command.linear_mps:.2f},{f.command.angular_radps:.2f}) "
                      f"age={f.sensor.age_s:.2f} valid={f.sensor.valid}")
                break
        else:
            continue
        break
    # Where was the robot when clearance was minimal?
    fmin = min(frames, key=lambda f: f.clearance_m)
    obs = fmin.obstacles[0]
    print(f"  min-clear frame: tick={fmin.tick} clear={fmin.clearance_m} "
          f"robot=({fmin.robot.x_m:.2f},{fmin.robot.y_m:.2f},{fmin.robot.yaw_rad:.2f}) "
          f"obs=({obs.x_m:.2f},{obs.y_m:.2f}) n_obs_seen={len(fmin.sensor.observations)}")
