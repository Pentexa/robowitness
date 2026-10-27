export interface Point2D {
  x_m: number;
  y_m: number;
}

export interface Pose2D {
  x_m: number;
  y_m: number;
  yaw_rad: number;
}

export interface WorldSpec {
  type: "warehouse";
  width_m: number;
  height_m: number;
  duration_limit_s: number;
  fixed_timestep_s: number;
}

export interface RobotSpec {
  kind: "differential_drive";
  start: Pose2D;
  goal: Point2D;
  goal_radius_m: number;
  body_radius_m: number;
  wheel_base_m: number;
  wheel_radius_m: number;
  sensor_range_m: number;
  sensor_latency_ms: number;
  sensor_noise_std_m: number;
}

export interface ObstacleSpec {
  id: string;
  shape: "circle";
  radius_m: number;
  motion: "static" | "ping_pong";
  start: Point2D;
  end: Point2D;
  speed_mps: number;
}

export interface OracleSpec {
  collision_free: boolean;
  min_clearance_m: number;
  must_reach_goal: boolean;
  max_duration_s: number;
  max_stuck_duration_s: number;
}

export interface ScenarioSpec {
  schema_version: "1.0";
  id: string;
  kind: "static_obstacle" | "dynamic_obstacle";
  seed: number;
  world: WorldSpec;
  robot: RobotSpec;
  obstacles: ObstacleSpec[];
  oracle: OracleSpec;
}

export interface PolicyConfig {
  schema_version: "1.0";
  id: string;
  max_speed_mps: number;
  safe_distance_m: number;
  reaction_margin_m: number;
  brake_gain: number;
  obstacle_prediction_horizon_s: number;
}

export interface ObstacleTelemetry {
  id: string;
  x_m: number;
  y_m: number;
  radius_m: number;
}

export interface EventRecord {
  event_id: string;
  type: string;
  tick: number;
  sim_time_s: number;
  details: Record<string, any>;
}

export interface TelemetryFrame {
  schema_version: "1.0";
  tick: number;
  sim_time_s: number;
  robot: Pose2D;
  obstacles: ObstacleTelemetry[];
  sensor: {
    sample_tick: number;
    delivered_tick: number;
    age_s: number;
    valid: boolean;
    observations: any[];
  };
  command: {
    linear_mps: number;
    angular_radps: number;
  };
  clearance_m: number;
  events: EventRecord[];
}

export interface RunMetrics {
  total_ticks: number;
  sim_duration_s: number;
  min_clearance_m: number;
  goal_reached: boolean;
  collision_detected: boolean;
  stuck_detected: boolean;
  timeout_detected: boolean;
}

export interface GateResult {
  gate_id: string;
  name: string;
  status: "PASS" | "FAIL" | "INCONCLUSIVE" | "NOT_RUN" | "RUNNING";
  reason_codes: string[];
  details: Record<string, any>;
}

export interface VerificationRecord {
  verification_id: string;
  job_id: string;
  baseline_run_id: string;
  candidate_policy: PolicyConfig;
  verdict: "VERIFIED_IN_SIMULATION" | "REJECTED" | "INCONCLUSIVE";
  gates: GateResult[];
  reason_codes: string[];
  artifact_dir: string;
  created_at: string;
  completed_at: string | null;
}
