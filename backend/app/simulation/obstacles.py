"""Simulation obstacles: static and deterministic ping-pong trajectories."""
import math
from typing import List, Tuple
import pybullet as p
from app.schemas.scenario import ObstacleSpec

class SimObstacle:
    def __init__(self, spec: ObstacleSpec, client_id: int):
        self.spec = spec
        self.client_id = client_id
        self.x_m = spec.start.x_m
        self.y_m = spec.start.y_m
        self.body_id = self._create_body()

        # Compute trajectory length and period
        dx = spec.end.x_m - spec.start.x_m
        dy = spec.end.y_m - spec.start.y_m
        self.dist_m = math.hypot(dx, dy)
        if self.spec.motion == "ping_pong" and self.dist_m > 0 and self.spec.speed_mps > 0:
            self.half_period_s = self.dist_m / self.spec.speed_mps
        else:
            self.half_period_s = 0.0

    def _create_body(self) -> int:
        col_shape = p.createCollisionShape(
            p.GEOM_CYLINDER,
            radius=self.spec.radius_m,
            height=0.5,
            physicsClientId=self.client_id
        )
        body = p.createMultiBody(
            baseMass=0.0,
            baseCollisionShapeIndex=col_shape,
            basePosition=[self.x_m, self.y_m, 0.25],
            physicsClientId=self.client_id
        )
        return body

    def update_position(self, sim_time_s: float) -> Tuple[float, float]:
        if self.spec.motion == "static" or self.half_period_s <= 0.0:
            self.x_m = self.spec.start.x_m
            self.y_m = self.spec.start.y_m
        else:
            # Deterministic triangular ping-pong phase
            cycle_time = 2.0 * self.half_period_s
            t_mod = sim_time_s % cycle_time
            if t_mod <= self.half_period_s:
                alpha = t_mod / self.half_period_s
            else:
                alpha = (cycle_time - t_mod) / self.half_period_s

            self.x_m = self.spec.start.x_m + alpha * (self.spec.end.x_m - self.spec.start.x_m)
            self.y_m = self.spec.start.y_m + alpha * (self.spec.end.y_m - self.spec.start.y_m)

        p.resetBasePositionAndOrientation(
            self.body_id,
            [self.x_m, self.y_m, 0.25],
            [0, 0, 0, 1],
            physicsClientId=self.client_id
        )
        return self.x_m, self.y_m
