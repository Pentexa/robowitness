"""Passive ROS 2 bridge: listens to /odom + /scan, writes import-ready JSONL.

SAFETY: This bridge NEVER publishes commands. It only records what the robot
already did, so a real drive can be judged later via POST /api/imports/telemetry.

Requires a ROS 2 environment (rclpy). Without ROS it exits with code 2 and an
honest message instead of pretending to work.

Usage (on the ROS machine):
    python scripts/ros2_bridge.py --output drive1.jsonl
Then upload drive1.jsonl in the RoboWitness "Karne" tab (Gerçek Sürüş Yükle).
"""
import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.ros_bridge.format import odom_to_frame, scan_min_distance  # noqa: E402


def yaw_from_quaternion(x: float, y: float, z: float, w: float) -> float:
    return math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))


def main() -> int:
    parser = argparse.ArgumentParser(description="Passive RoboWitness ROS 2 recorder")
    parser.add_argument("--output", default="ros_drive.jsonl", help="JSONL output file")
    parser.add_argument("--odom-topic", default="/odom")
    parser.add_argument("--scan-topic", default="/scan")
    args = parser.parse_args()

    try:
        import rclpy
        from rclpy.node import Node
        from nav_msgs.msg import Odometry
        from sensor_msgs.msg import LaserScan
    except ImportError:
        print("[BLOCKED] rclpy / ROS 2 mesaj paketleri bulunamadı.")
        print("  Bu köprü yalnızca ROS 2 kurulu bir makinede çalışır; ana RoboWitness")
        print("  backend'i ROS olmadan çalışmaya devam eder. ROS ortamında tekrar deneyin:")
        print("    source /opt/ros/<distro>/setup.bash && python scripts/ros2_bridge.py")
        return 2

    latest_scan = {"min_distance": None}
    out = open(args.output, "w", encoding="utf-8")

    class PassiveRecorder(Node):
        def __init__(self):
            super().__init__("robowitness_passive_bridge")
            self.create_subscription(LaserScan, args.scan_topic, self.on_scan, 10)
            self.create_subscription(Odometry, args.odom_topic, self.on_odom, 10)
            self.count = 0

        def on_scan(self, msg):
            latest_scan["min_distance"] = scan_min_distance(
                list(msg.ranges), float(msg.range_min), float(msg.range_max)
            )

        def on_odom(self, msg):
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            pos = msg.pose.pose.position
            ori = msg.pose.pose.orientation
            frame = odom_to_frame(
                {
                    "stamp_s": stamp,
                    "x_m": pos.x,
                    "y_m": pos.y,
                    "yaw_rad": yaw_from_quaternion(ori.x, ori.y, ori.z, ori.w),
                },
                latest_scan["min_distance"],
            )
            out.write(json.dumps(frame) + "\n")
            out.flush()
            self.count += 1

    rclpy.init()
    node = PassiveRecorder()
    print(f"[bridge] Dinleniyor (pasif, komut GÖNDERİLMEZ): {args.odom_topic} + {args.scan_topic}")
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        print(f"[bridge] {node.count} kare yazıldı: {args.output}")
        out.close()
        node.destroy_node()
        rclpy.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
