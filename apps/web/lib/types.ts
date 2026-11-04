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

export type RobotDriveType =
  | "differential_drive"
  | "ackermann"
  | "omnidirectional"
  | "tracked"
  | "quadruped"
  | "other";

export interface RobotProfileInput {
  brand: string;
  model: string;
  variant: string;
  year: number | null;
  drive_type: RobotDriveType;
  body_radius_m: number;
  wheel_base_m: number | null;
  wheel_radius_m: number | null;
  weight_kg: number | null;
  max_speed_mps: number | null;
  max_payload_kg: number | null;
  sensor_type: string;
  sensor_range_m: number;
  sensor_latency_ms: number;
  sensor_noise_std_m: number;
  compute_unit: string;
  operating_system: string;
  battery_wh: number | null;
  notes: string;
}

export interface RobotProfile extends RobotProfileInput {
  robot_id: string;
  source: "builtin" | "user";
  created_at: string;
  updated_at: string;
  simulation_compatible: boolean;
  compatibility_issues: string[];
}

export interface ScenarioCatalogEntry {
  scenario: ScenarioSpec;
  title: string;
  description: string;
  difficulty: string;
  category: string;
  tags: string[];
}

export interface LocalPolicyInfo {
  enabled: boolean;
  policies: Array<{ name: string; file: string; description: string }>;
}

export interface PolicyProfileInput {
  name: string;
  description: string;
  policy: PolicyConfig;
}

export interface PolicyProfile extends PolicyProfileInput {
  profile_id: string;
  source: "builtin" | "user";
  created_at: string;
  updated_at: string;
}

export interface BatteryEntry {
  scenario_id: string;
  title: string;
  run_id: string;
  oracle_status: OracleStatus;
  reason_codes: string[];
  metrics: RunMetrics;
  near_miss: boolean;
}

export interface BatterySummary {
  total: number;
  passed: number;
  failed: number;
  inconclusive: number;
  collisions: number;
  near_misses: number;
  worst_clearance_m: number | null;
}

export interface BatteryResult {
  battery_id: string;
  robot_id: string;
  robot_label: string;
  policy_id: string;
  entries: BatteryEntry[];
  summary: BatterySummary;
  created_at: string;
  completed_at: string | null;
}

export interface ImportResult {
  import_id: string;
  name: string;
  robot_label: string;
  provenance: "REAL_LOG";
  oracle_status: OracleStatus;
  reason_codes: string[];
  near_miss: boolean;
  metrics: {
    frame_count: number;
    duration_s: number;
    min_clearance_m: number | null;
    collision_detected: boolean;
    goal_reached: boolean | null;
    final_goal_distance_m: number | null;
    path_length_m: number;
  };
  created_at: string;
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

export interface PolicyPatch {
  max_speed_mps?: number;
  safe_distance_m?: number;
  reaction_margin_m?: number;
  brake_gain?: number;
  obstacle_prediction_horizon_s?: number;
}

export interface InvestigationResponse {
  investigation_id: string;
  run_id: string;
  failure_tick: number;
  hypothesis: string;
  evidence_summary: string;
  suggested_patch: PolicyPatch;
  provenance: "LIVE_META" | "OFFLINE_REFERENCE" | "UNAVAILABLE";
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
  details: Record<string, unknown>;
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
    observations: unknown[];
  };
  command: {
    linear_mps: number;
    angular_radps: number;
  };
  clearance_m: number;
  events: EventRecord[];
}

export type OracleStatus = "PASS" | "FAIL" | "INCONCLUSIVE";

export interface RunResult {
  run_id: string;
  scenario_id: string;
  scenario_hash: string;
  policy_hash: string;
  job_status: string;
  oracle_status: OracleStatus;
  reason_codes: string[];
  metrics: RunMetrics;
  artifact_path: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
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
  details: Record<string, unknown>;
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

export interface StressCell {
  latency_ms: number;
  noise_std_m: number;
  run_id: string;
  oracle_status: OracleStatus;
  reason_codes: string[];
  metrics: RunMetrics;
  near_miss: boolean;
}

export interface StressTestResult {
  stress_id: string;
  scenario_id: string;
  policy_id: string;
  latencies_ms: number[];
  noise_levels_m: number[];
  cells: StressCell[];
  summary: {
    total: number;
    passed: number;
    failed: number;
    inconclusive: number;
    near_misses: number;
    worst_clearance_m: number | null;
  };
  created_at: string;
  completed_at: string | null;
}

export interface AdversarialRound {
  iteration: number;
  scenario_id: string | null;
  provenance: "LIVE_META" | "OFFLINE_REFERENCE" | "UNAVAILABLE";
  executed: boolean;
  run_id: string | null;
  oracle_status: OracleStatus | null;
  reason_codes: string[];
  min_clearance_m: number | null;
  note: string;
}

export interface AdversarialResult {
  adversarial_id: string;
  policy_id: string;
  max_iterations: number;
  rounds: AdversarialRound[];
  executed_count: number;
  fail_count: number;
  pass_count: number;
  total_tokens_used: number;
  stopped_reason: string;
  created_at: string;
  completed_at: string | null;
}

export interface InspectedFile {
  name: string;
  status: "OK" | "MISMATCH" | "MISSING" | "NOT_SEALED" | "EXTRA";
  sha256: string | null;
  expected_sha256: string | null;
  size_bytes: number;
}

export interface EvidenceInspectReport {
  ok: boolean;
  package_type: "verification" | "run" | "unknown";
  package_id: string | null;
  verdict: string | null;
  oracle_status: string | null;
  files: InspectedFile[];
  errors: string[];
  file_count: number;
}
