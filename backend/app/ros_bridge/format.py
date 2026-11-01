"""Convert ROS 2 odometry/scan readings into RoboWitness import frames.

These functions take plain dicts/lists so they can be unit-tested without a
ROS installation. The live bridge script (scripts/ros2_bridge.py) is the only
place that touches rclpy, and it only listens — it never sends commands.
"""

import math
from typing import Optional


def scan_min_distance(
    ranges, range_min: float = 0.0, range_max: float = float("inf")
) -> Optional[float]:
    """Smallest valid laser range; inf/nan/out-of-range readings are ignored."""
    valid = [
        float(r)
        for r in ranges
        if r is not None and math.isfinite(float(r)) and range_min <= float(r) <= range_max
    ]
    return min(valid) if valid else None


def odom_to_frame(odom: dict, min_obstacle_distance_m: Optional[float]) -> dict:
    """odom: {stamp_s, x_m, y_m, yaw_rad} -> one import frame dict."""
    return {
        "t_s": float(odom["stamp_s"]),
        "x_m": float(odom["x_m"]),
        "y_m": float(odom["y_m"]),
        "yaw_rad": float(odom.get("yaw_rad", 0.0)),
        "min_obstacle_distance_m": min_obstacle_distance_m,
    }


def frames_to_import_payload(frames: list[dict], name: str, robot_label: str = "") -> dict:
    """Build the JSON body for POST /api/imports/telemetry from bridge frames."""
    import json

    return {
        "name": name,
        "robot_label": robot_label,
        "format": "json",
        "content": json.dumps({"frames": frames}),
    }
