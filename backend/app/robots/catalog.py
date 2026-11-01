"""Built-in robot catalog seed entries.

Specs are nominal example values entered for the catalog (footprint radius is
the circumscribed circle of the manufacturer's published footprint where
known). They are labeled ``builtin`` examples, are not manufacturer-certified
measurements, and can be corrected by adding a user entry. Entries whose
drive type or size the differential-drive simulator cannot represent are
kept in the catalog but marked simulation-incompatible by the schema layer.
"""

from app.schemas.robot_profile import RobotProfile, RobotProfileCreate, build_profile

_SEED_TS = "2026-01-01T00:00:00+00:00"

_SEEDS: list[tuple[str, dict]] = [
    (
        "robot-turtlebot3-waffle-pi",
        dict(
            brand="ROBOTIS",
            model="TurtleBot3 Waffle Pi",
            drive_type="differential_drive",
            body_radius_m=0.21,
            wheel_base_m=0.287,
            wheel_radius_m=0.033,
            weight_kg=1.8,
            max_speed_mps=0.26,
            max_payload_kg=30.0,
            sensor_type="LDS-01 360° LiDAR",
            sensor_range_m=3.5,
            sensor_latency_ms=100,
            sensor_noise_std_m=0.01,
            compute_unit="Raspberry Pi 3",
            operating_system="ROS 1 / Ubuntu",
            notes="Eğitim ve araştırma için yaygın, küçük diferansiyel sürüşlü robot (örnek katalog değeri).",
        ),
    ),
    (
        "robot-turtlebot3-burger",
        dict(
            brand="ROBOTIS",
            model="TurtleBot3 Burger",
            drive_type="differential_drive",
            body_radius_m=0.105,
            wheel_base_m=0.16,
            wheel_radius_m=0.033,
            weight_kg=1.0,
            max_speed_mps=0.22,
            max_payload_kg=15.0,
            sensor_type="LDS-01 360° LiDAR",
            sensor_range_m=3.5,
            sensor_latency_ms=100,
            sensor_noise_std_m=0.01,
            compute_unit="Raspberry Pi 3",
            operating_system="ROS 1 / Ubuntu",
            notes="Gövde yarıçapı simülatör alt sınırının (0.15 m) altında; testte kullanılamaz, katalogda bilgi amaçlı durur.",
        ),
    ),
    (
        "robot-jackal",
        dict(
            brand="Clearpath Robotics",
            model="Jackal UGV",
            drive_type="differential_drive",
            body_radius_m=0.33,
            wheel_base_m=0.375,
            wheel_radius_m=0.095,
            weight_kg=17.0,
            max_speed_mps=2.0,
            max_payload_kg=20.0,
            sensor_type="2D LiDAR (opsiyonel)",
            sensor_range_m=10.0,
            sensor_latency_ms=50,
            sensor_noise_std_m=0.01,
            compute_unit="x86 onboard PC",
            operating_system="ROS / Ubuntu",
            notes="Dış mekân araştırma UGV'si (örnek katalog değeri).",
        ),
    ),
    (
        "robot-mir250",
        dict(
            brand="Mobile Industrial Robots",
            model="MiR250",
            drive_type="differential_drive",
            body_radius_m=0.49,
            wheel_base_m=0.6,
            weight_kg=83.0,
            max_speed_mps=2.0,
            max_payload_kg=250.0,
            sensor_type="360° güvenlik LiDAR",
            sensor_range_m=8.0,
            sensor_latency_ms=80,
            sensor_noise_std_m=0.01,
            notes="Endüstriyel otonom mobil robot. Gövde yarıçapı simülatör üst sınırının (0.40 m) üstünde; katalogda bilgi amaçlı durur.",
        ),
    ),
    (
        "robot-spot",
        dict(
            brand="Boston Dynamics",
            model="Spot",
            drive_type="quadruped",
            body_radius_m=0.55,
            weight_kg=32.5,
            max_speed_mps=1.6,
            max_payload_kg=14.0,
            sensor_type="Derinlik kameraları + LiDAR (opsiyonel)",
            sensor_range_m=4.0,
            sensor_latency_ms=100,
            sensor_noise_std_m=0.02,
            notes="Dört bacaklı robot. Simülatör yalnızca diferansiyel sürüşü desteklediği için testte kullanılamaz.",
        ),
    ),
    (
        "robot-go2",
        dict(
            brand="Unitree",
            model="Go2",
            drive_type="quadruped",
            body_radius_m=0.35,
            weight_kg=15.0,
            max_speed_mps=2.5,
            max_payload_kg=8.0,
            sensor_type="4D LiDAR L1",
            sensor_range_m=10.0,
            sensor_latency_ms=80,
            sensor_noise_std_m=0.02,
            notes="Dört bacaklı robot. Simülatör yalnızca diferansiyel sürüşü desteklediği için testte kullanılamaz.",
        ),
    ),
]


def builtin_robots() -> list[RobotProfile]:
    return [
        build_profile(RobotProfileCreate(**data), robot_id, "builtin", _SEED_TS, _SEED_TS)
        for robot_id, data in _SEEDS
    ]
