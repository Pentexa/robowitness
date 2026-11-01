"""Planar differential-drive robot kinematics and PyBullet collision representation."""

import math
import pybullet as p
from app.schemas.policy import ControlCommand
from app.schemas.scenario import Pose2D, RobotSpec


class SimRobot:
    def __init__(self, spec: RobotSpec, client_id: int):
        self.spec = spec
        self.client_id = client_id
        self.pose = Pose2D(x_m=spec.start.x_m, y_m=spec.start.y_m, yaw_rad=spec.start.yaw_rad)
        self.body_id = self._create_body()

    def _create_body(self) -> int:
        col_shape = p.createCollisionShape(
            p.GEOM_CYLINDER,
            radius=self.spec.body_radius_m,
            height=0.3,
            physicsClientId=self.client_id,
        )
        body = p.createMultiBody(
            baseMass=5.0,
            baseCollisionShapeIndex=col_shape,
            basePosition=[self.pose.x_m, self.pose.y_m, 0.15],
            baseOrientation=p.getQuaternionFromEuler([0, 0, self.pose.yaw_rad]),
            physicsClientId=self.client_id,
        )
        return body

    def step_motion(self, cmd: ControlCommand, dt: float) -> Pose2D:
        """Apply bounded forward and angular velocity differential-drive kinematics."""
        new_yaw = self.pose.yaw_rad + cmd.angular_radps * dt
        # Normalize yaw to [-pi, pi)
        new_yaw = (new_yaw + math.pi) % (2.0 * math.pi) - math.pi

        new_x = self.pose.x_m + cmd.linear_mps * math.cos(self.pose.yaw_rad) * dt
        new_y = self.pose.y_m + cmd.linear_mps * math.sin(self.pose.yaw_rad) * dt

        self.pose = Pose2D(x_m=new_x, y_m=new_y, yaw_rad=new_yaw)

        # Update PyBullet body pose
        quat = p.getQuaternionFromEuler([0, 0, new_yaw])
        p.resetBasePositionAndOrientation(
            self.body_id, [new_x, new_y, 0.15], quat, physicsClientId=self.client_id
        )
        return self.pose
