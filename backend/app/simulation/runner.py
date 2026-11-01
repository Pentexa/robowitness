"""Authoritative 1/60-second simulation loop runner."""

import math
from typing import List, Tuple
import pybullet as p
from app.schemas.policy import PolicyConfig
from app.schemas.scenario import ScenarioSpec
from app.schemas.telemetry import (
    CommandTelemetry,
    EventRecord,
    ObstacleTelemetry,
    RunMetrics,
    SensorTelemetry,
    TelemetryFrame,
)
from app.simulation.obstacles import SimObstacle
from app.simulation.robot import SimRobot
from app.simulation.sensors import SensorSystem
from app.simulation.world import SimulationWorld


class SimulationRunner:
    def __init__(self, scenario: ScenarioSpec, policy_config: PolicyConfig, policy_fn):
        self.scenario = scenario
        self.policy_config = policy_config
        self.policy_fn = policy_fn
        self.dt = scenario.world.fixed_timestep_s
        self.max_ticks = int(scenario.world.duration_limit_s / self.dt)

    def run(self) -> Tuple[List[TelemetryFrame], RunMetrics, List[str]]:
        world = SimulationWorld(self.scenario.world)
        client_id = world.connect()

        frames: List[TelemetryFrame] = []
        reason_codes: List[str] = []
        min_clearance_recorded = float("inf")
        goal_reached = False
        collision_detected = False
        stuck_detected = False
        timeout_detected = False

        try:
            robot = SimRobot(self.scenario.robot, client_id)
            obstacles = [SimObstacle(obs, client_id) for obs in self.scenario.obstacles]
            sensor_sys = SensorSystem(self.scenario.robot, self.dt, self.scenario.seed)

            last_goal_dist = math.hypot(
                self.scenario.robot.goal.x_m - robot.pose.x_m,
                self.scenario.robot.goal.y_m - robot.pose.y_m,
            )
            ticks_without_progress = 0
            stuck_tick_threshold = int(self.scenario.oracle.max_stuck_duration_s / self.dt)

            for tick in range(self.max_ticks):
                sim_time_s = round(tick * self.dt, 6)

                # 1. Update obstacles
                true_obs_positions = []
                obs_telemetry = []
                for sim_obs in obstacles:
                    ox, oy = sim_obs.update_position(sim_time_s)
                    true_obs_positions.append(
                        {
                            "id": sim_obs.spec.id,
                            "x_m": ox,
                            "y_m": oy,
                            "radius_m": sim_obs.spec.radius_m,
                        }
                    )
                    obs_telemetry.append(
                        ObstacleTelemetry(
                            id=sim_obs.spec.id,
                            x_m=ox,
                            y_m=oy,
                            radius_m=sim_obs.spec.radius_m,
                        )
                    )

                # 2. Sensor pipeline: deliver due observation, queue current truth for future
                sensor_sys.capture_observation(tick, sim_time_s, robot.pose, true_obs_positions)
                delivered_obs = sensor_sys.get_delivered_observation(tick, sim_time_s)

                # 3. Policy execution (sees ONLY delivered observation and allowed config)
                cmd = self.policy_fn(delivered_obs, self.policy_config)

                # 4. Robot motion integration
                new_pose = robot.step_motion(cmd, self.dt)

                # 5. Physics collision step
                p.performCollisionDetection(physicsClientId=client_id)

                # 6. Contact and clearance evaluation
                tick_events: List[EventRecord] = []

                # Wall clearances
                w = self.scenario.world.width_m
                h = self.scenario.world.height_m
                r_rad = self.scenario.robot.body_radius_m
                wall_clearance = min(
                    new_pose.x_m - r_rad,
                    w - r_rad - new_pose.x_m,
                    new_pose.y_m - r_rad,
                    h - r_rad - new_pose.y_m,
                )

                # Obstacle clearances
                obs_clearance = float("inf")
                for tobs in true_obs_positions:
                    center_d = math.hypot(tobs["x_m"] - new_pose.x_m, tobs["y_m"] - new_pose.y_m)
                    surf_d = center_d - tobs["radius_m"] - r_rad
                    if surf_d < obs_clearance:
                        obs_clearance = surf_d

                current_clearance = min(wall_clearance, obs_clearance)
                if current_clearance < min_clearance_recorded:
                    min_clearance_recorded = current_clearance

                # Check PyBullet contacts
                contact_points = p.getContactPoints(robot.body_id, physicsClientId=client_id)
                if len(contact_points) > 0 or current_clearance <= 1e-4:
                    collision_detected = True
                    tick_events.append(
                        EventRecord(
                            event_id=f"evt-col-{tick}",
                            type="COLLISION",
                            tick=tick,
                            sim_time_s=sim_time_s,
                            details={"clearance_m": round(current_clearance, 4)},
                        )
                    )
                    if "COLLISION" not in reason_codes:
                        reason_codes.append("COLLISION")

                # Check minimum clearance violation
                if (
                    current_clearance < self.scenario.oracle.min_clearance_m
                    and not collision_detected
                ):
                    if "MIN_CLEARANCE_VIOLATION" not in reason_codes:
                        reason_codes.append("MIN_CLEARANCE_VIOLATION")

                # Check goal reached
                dist_to_goal = math.hypot(
                    self.scenario.robot.goal.x_m - new_pose.x_m,
                    self.scenario.robot.goal.y_m - new_pose.y_m,
                )
                if dist_to_goal <= self.scenario.robot.goal_radius_m:
                    goal_reached = True
                    tick_events.append(
                        EventRecord(
                            event_id=f"evt-goal-{tick}",
                            type="GOAL_REACHED",
                            tick=tick,
                            sim_time_s=sim_time_s,
                            details={"distance_m": round(dist_to_goal, 4)},
                        )
                    )

                # Check stuck progress
                if (last_goal_dist - dist_to_goal) < 0.005:  # Less than 5mm progress
                    ticks_without_progress += 1
                    if ticks_without_progress >= stuck_tick_threshold:
                        stuck_detected = True
                        if "STUCK" not in reason_codes:
                            reason_codes.append("STUCK")
                else:
                    ticks_without_progress = 0
                    last_goal_dist = dist_to_goal

                # Assemble TelemetryFrame
                frame = TelemetryFrame(
                    tick=tick,
                    sim_time_s=sim_time_s,
                    robot=new_pose,
                    obstacles=obs_telemetry,
                    sensor=SensorTelemetry(
                        sample_tick=delivered_obs.sample_tick,
                        delivered_tick=delivered_obs.delivered_tick,
                        age_s=delivered_obs.age_s,
                        valid=delivered_obs.valid,
                        observations=[
                            {"id": o.id, "dist": o.distance_m} for o in delivered_obs.obstacles
                        ],
                    ),
                    command=CommandTelemetry(
                        linear_mps=cmd.linear_mps, angular_radps=cmd.angular_radps
                    ),
                    clearance_m=round(current_clearance, 4),
                    events=tick_events,
                )
                frames.append(frame)

                # Termination conditions: collision or goal reached
                if collision_detected or goal_reached:
                    break

            if not goal_reached and not collision_detected:
                timeout_detected = True
                if "TIMEOUT" not in reason_codes:
                    reason_codes.append("TIMEOUT")

        finally:
            world.disconnect()

        metrics = RunMetrics(
            total_ticks=len(frames),
            sim_duration_s=round(len(frames) * self.dt, 4),
            min_clearance_m=round(min_clearance_recorded, 4),
            goal_reached=goal_reached,
            collision_detected=collision_detected,
            stuck_detected=stuck_detected,
            timeout_detected=timeout_detected,
        )

        return frames, metrics, reason_codes
