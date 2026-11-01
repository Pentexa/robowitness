"""Convert a text occupancy grid into a validated ScenarioSpec.

Grid characters: '#' blocked, '.' free, 'S' start, 'G' goal.
Each connected blocked cluster becomes one circle obstacle (centroid +
covering radius, clamped to the simulator's obstacle limits). World size is
cols*cell_size by rows*cell_size and must fit the ScenarioSpec world limits.
"""

import hashlib
import math
from collections import deque

from app.schemas.scenario import (
    ObstacleSpec,
    OracleSpec,
    Point2D,
    Pose2D,
    RobotSpec,
    ScenarioSpec,
    WorldSpec,
)

MAX_OBSTACLES = 8


def _clusters(grid: list[str]) -> list[list[tuple[int, int]]]:
    rows, cols = len(grid), len(grid[0])
    seen: set[tuple[int, int]] = set()
    clusters: list[list[tuple[int, int]]] = []
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] != "#" or (r, c) in seen:
                continue
            cluster: list[tuple[int, int]] = []
            queue = deque([(r, c)])
            seen.add((r, c))
            while queue:
                cr, cc = queue.popleft()
                cluster.append((cr, cc))
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = cr + dr, cc + dc
                    if (
                        0 <= nr < rows
                        and 0 <= nc < cols
                        and grid[nr][nc] == "#"
                        and (nr, nc) not in seen
                    ):
                        seen.add((nr, nc))
                        queue.append((nr, nc))
            clusters.append(cluster)
    return clusters


def convert_grid_to_scenario(
    name: str,
    grid_text: str,
    cell_size_m: float = 0.5,
) -> tuple[ScenarioSpec, list[str]]:
    warnings: list[str] = []
    lines = [line.rstrip("\n") for line in grid_text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("Grid is empty")
    width_cells = max(len(line) for line in lines)
    lines = [line.ljust(width_cells, ".") for line in lines]
    rows, cols = len(lines), width_cells

    world_w = round(cols * cell_size_m, 3)
    world_h = round(rows * cell_size_m, 3)
    if not (6.0 <= world_w <= 20.0 and 4.0 <= world_h <= 15.0):
        raise ValueError(
            f"Map size {world_w}x{world_h} m does not fit simulator world limits "
            "(width 6-20 m, height 4-15 m); adjust cell_size_m"
        )

    def to_xy(r: int, c: int) -> tuple[float, float]:
        return (c + 0.5) * cell_size_m, world_h - (r + 0.5) * cell_size_m

    start_xy: tuple[float, float] | None = None
    goal_xy: tuple[float, float] | None = None
    for r in range(rows):
        for c, ch in enumerate(lines[r]):
            if ch == "S":
                start_xy = to_xy(r, c)
            elif ch == "G":
                goal_xy = to_xy(r, c)
    if start_xy is None:
        # Default: free cell nearest bottom-left.
        for r in range(rows - 1, -1, -1):
            for c in range(cols):
                if lines[r][c] == ".":
                    start_xy = to_xy(r, c)
                    break
            if start_xy:
                break
    if goal_xy is None:
        for r in range(rows - 1, -1, -1):
            for c in range(cols - 1, -1, -1):
                if lines[r][c] == ".":
                    goal_xy = to_xy(r, c)
                    break
            if goal_xy:
                break
    if start_xy is None or goal_xy is None:
        raise ValueError("Grid needs at least two free cells (or S/G markers)")

    clusters = _clusters(lines)
    clusters.sort(key=len, reverse=True)
    if len(clusters) > MAX_OBSTACLES:
        warnings.append(
            f"{len(clusters)} engel kümesi bulundu; en büyük {MAX_OBSTACLES} tanesi alındı, "
            "diğerleri atlandı."
        )
        clusters = clusters[:MAX_OBSTACLES]

    obstacles: list[ObstacleSpec] = []
    for idx, cluster in enumerate(clusters, start=1):
        pts = [to_xy(r, c) for r, c in cluster]
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        radius = max(math.hypot(px - cx, py - cy) for px, py in pts) + cell_size_m / 2
        clamped = max(0.15, min(0.80, radius))
        if clamped != radius:
            warnings.append(f"Engel O{idx} yarıçapı {radius:.2f} m → {clamped} m'ye kırpıldı.")
        obstacles.append(
            ObstacleSpec(
                id=f"O{idx}",
                radius_m=round(clamped, 3),
                motion="static",
                start=Point2D(x_m=round(cx, 3), y_m=round(cy, 3)),
                end=Point2D(x_m=round(cx, 3), y_m=round(cy, 3)),
                speed_mps=0.0,
            )
        )

    digest = hashlib.sha256(grid_text.encode()).hexdigest()[:6]
    scenario = ScenarioSpec(
        id=f"RW-MAP-{digest}",
        kind="static_obstacle",
        seed=4200,
        world=WorldSpec(width_m=world_w, height_m=world_h, duration_limit_s=30.0),
        robot=RobotSpec(
            start=Pose2D(x_m=round(start_xy[0], 3), y_m=round(start_xy[1], 3), yaw_rad=0.0),
            goal=Point2D(x_m=round(goal_xy[0], 3), y_m=round(goal_xy[1], 3)),
            goal_radius_m=0.35,
            body_radius_m=0.25,
            sensor_latency_ms=0,
            sensor_noise_std_m=0.0,
        ),
        obstacles=obstacles,
        oracle=OracleSpec(max_duration_s=30.0),
    )
    return scenario, warnings
