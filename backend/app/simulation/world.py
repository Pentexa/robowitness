"""PyBullet DIRECT world setup and boundary collision bodies."""
from typing import Optional
import pybullet as p
from app.schemas.scenario import WorldSpec

class SimulationWorld:
    """Manages PyBullet physics connection and warehouse walls."""
    def __init__(self, world_spec: WorldSpec):
        self.spec = world_spec
        self.client_id: Optional[int] = None
        self.wall_ids = []

    def connect(self) -> int:
        self.client_id = p.connect(p.DIRECT)
        p.setTimeStep(self.spec.fixed_timestep_s, physicsClientId=self.client_id)
        p.setGravity(0, 0, 0, physicsClientId=self.client_id)
        self._build_walls()
        return self.client_id

    def _build_walls(self) -> None:
        """Create bounding walls around warehouse [0, width] x [0, height]."""
        w = self.spec.width_m
        h = self.spec.height_m
        wall_thickness = 0.2
        # Wall definitions: center_x, center_y, half_extents_x, half_extents_y
        segments = [
            (w / 2.0, -wall_thickness / 2.0, w / 2.0 + wall_thickness, wall_thickness / 2.0), # Bottom
            (w / 2.0, h + wall_thickness / 2.0, w / 2.0 + wall_thickness, wall_thickness / 2.0), # Top
            (-wall_thickness / 2.0, h / 2.0, wall_thickness / 2.0, h / 2.0 + wall_thickness), # Left
            (w + wall_thickness / 2.0, h / 2.0, wall_thickness / 2.0, h / 2.0 + wall_thickness), # Right
        ]
        for cx, cy, hx, hy in segments:
            col_shape = p.createCollisionShape(
                p.GEOM_BOX,
                halfExtents=[hx, hy, 0.5],
                physicsClientId=self.client_id
            )
            body = p.createMultiBody(
                baseMass=0.0,
                baseCollisionShapeIndex=col_shape,
                basePosition=[cx, cy, 0.25],
                physicsClientId=self.client_id
            )
            self.wall_ids.append(body)

    def disconnect(self) -> None:
        if self.client_id is not None:
            try:
                p.disconnect(physicsClientId=self.client_id)
            finally:
                self.client_id = None
                self.wall_ids.clear()
