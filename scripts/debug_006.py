import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.runner import SimulationRunner

by_id = {}
for name in ("manifest_v2_eval.json",):
    for s in json.load(open(ROOT / "scenarios" / "holdout" / name))["scenarios"]:
        by_id[s["id"]] = s
spec = ScenarioSpec.model_validate(by_id["RW-HLD2-006"])
F1 = PolicyConfig(id="x", max_speed_mps=0.60, safe_distance_m=1.00,
                  reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.00)

# Replicate runner loop with instrumentation on the interesting window.
from app.simulation.obstacles import SimObstacle
from app.simulation.robot import SimRobot
from app.simulation.sensors import SensorSystem
from app.simulation.world import SimulationWorld

world = SimulationWorld(spec.world)
cid = world.connect()
try:
    robot = SimRobot(spec.robot, cid)
    obstacles = [SimObstacle(o, cid) for o in spec.obstacles]
    sens = SensorSystem(spec.robot, spec.world.fixed_timestep_s, spec.seed)
    import pybullet as p
    for tick in range(810):
        t = round(tick * spec.world.fixed_timestep_s, 6)
        true_pos = [ob.update_position(t) for ob in obstacles]
        sens.capture_observation(tick, t, robot.pose, [
            {"id": o.spec.id, "x_m": x, "y_m": y, "radius_m": o.spec.radius_m}
            for o, (x, y) in zip(obstacles, true_pos)])
        dobs = sens.get_delivered_observation(tick, t)
        cmd = configurable_policy(dobs, F1)
        robot.step_motion(cmd, spec.world.fixed_timestep_s)
        p.performCollisionDetection(physicsClientId=cid)
        if 740 <= tick <= 800 and tick % 5 == 0:
            import math
            ox, oy = true_pos[0]
            d = math.hypot(ox - robot.pose.x_m, oy - robot.pose.y_m) - 0.32 - 0.25
            tr = dobs.tracks[0] if dobs.tracks else None
            print("tick=%d robot=(%.2f,%.2f) obs=(%.2f,%.2f) true_d=%.2f cmd=(%.2f,%.2f) age=%.2f nobs=%d %s"
                  % (tick, robot.pose.x_m, robot.pose.y_m, ox, oy, d,
                     cmd.linear_mps, cmd.angular_radps, dobs.age_s, len(dobs.obstacles),
                     ("vx=%.2f vy=%.2f conf=%s" % (tr.vx_mps, tr.vy_mps, tr.confident)) if tr else "no-track"),
                  flush=True)
finally:
    world.disconnect()
