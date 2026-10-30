import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.policies.configurable import configurable_policy
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.simulation.obstacles import SimObstacle
from app.simulation.robot import SimRobot
from app.simulation.sensors import SensorSystem
from app.simulation.world import SimulationWorld

by_id = {}
for s in json.load(open(ROOT / "scenarios" / "holdout" / "manifest_v2_eval.json"))["scenarios"]:
    by_id[s["id"]] = s
spec = ScenarioSpec.model_validate(by_id["RW-HLD2-017"])
F1 = PolicyConfig(id="x", max_speed_mps=0.60, safe_distance_m=1.00,
                  reaction_margin_m=0.20, brake_gain=4.0, obstacle_prediction_horizon_s=1.00)
o = spec.obstacles[0]
print("obs x=%.2f y %.2f->%.2f r=%.2f v=%.2f lat=%d noise=%.2f" % (
    o.start.x_m, o.start.y_m, o.end.y_m, o.radius_m, o.speed_mps,
    spec.robot.sensor_latency_ms, spec.robot.sensor_noise_std_m), flush=True)

world = SimulationWorld(spec.world)
cid = world.connect()
try:
    import pybullet as p
    robot = SimRobot(spec.robot, cid)
    obstacles = [SimObstacle(ob, cid) for ob in spec.obstacles]
    sens = SensorSystem(spec.robot, spec.world.fixed_timestep_s, spec.seed)
    for tick in range(700):
        t = round(tick * spec.world.fixed_timestep_s, 6)
        true_pos = [ob.update_position(t) for ob in obstacles]
        sens.capture_observation(tick, t, robot.pose, [
            {"id": ob.spec.id, "x_m": x, "y_m": y, "radius_m": ob.spec.radius_m}
            for ob, (x, y) in zip(obstacles, true_pos)])
        dobs = sens.get_delivered_observation(tick, t)
        cmd = configurable_policy(dobs, F1)
        robot.step_motion(cmd, spec.world.fixed_timestep_s)
        p.performCollisionDetection(physicsClientId=cid)
        if 540 <= tick <= 660 and tick % 4 == 0:
            ox, oy = true_pos[0]
            d = math.hypot(ox - robot.pose.x_m, oy - robot.pose.y_m) - 0.34 - 0.25
            tr = dobs.tracks[0] if dobs.tracks else None
            print("tick=%d robot=(%.2f,%.2f) obs=(%.2f,%.2f) true_d=%.2f cmd=(%.2f,%.2f) %s"
                  % (tick, robot.pose.x_m, robot.pose.y_m, ox, oy, d,
                     cmd.linear_mps, cmd.angular_radps,
                     ("vx=%.2f vy=%.2f" % (tr.vx_mps, tr.vy_mps)) if tr else "no-track"),
                  flush=True)
finally:
    world.disconnect()
