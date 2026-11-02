import {
  BatteryResult,
  ImportResult,
  LocalPolicyInfo,
  PolicyConfig,
  PolicyProfile,
  PolicyProfileInput,
  RobotProfile,
  RobotProfileInput,
  RunResult,
  ScenarioCatalogEntry,
  ScenarioSpec,
  TelemetryFrame,
  VerificationRecord,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_RW_API_URL || "http://localhost:8000";

export const API_BASE_URL = API_BASE;

/** Enterprise auth: keys live in localStorage, never in source code. */
export function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  try {
    const key = localStorage.getItem("rw_api_key");
    const ws = localStorage.getItem("rw_workspace");
    const jwt = localStorage.getItem("rw_jwt");
    if (key) headers["X-API-Key"] = key;
    if (ws) headers["X-Workspace-Id"] = ws;
    if (jwt) headers["Authorization"] = `Bearer ${jwt}`;
  } catch {
    /* localStorage unavailable */
  }
  return headers;
}

async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: { ...authHeaders(), ...((init.headers as Record<string, string>) || {}) },
  });
}

export async function fetchHealth() {
  const res = await apiFetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchReferenceScenarios(): Promise<ScenarioSpec[]> {
  const res = await apiFetch(`${API_BASE}/api/scenarios/reference`);
  if (!res.ok) throw new Error("Failed to load reference scenarios");
  return res.json();
}

export async function fetchScenarioLibrary(): Promise<ScenarioCatalogEntry[]> {
  const res = await apiFetch(`${API_BASE}/api/scenarios/library`);
  if (!res.ok) throw new Error("Failed to load scenario library");
  return res.json();
}

export async function fetchRobots(): Promise<RobotProfile[]> {
  const res = await apiFetch(`${API_BASE}/api/robots`);
  if (!res.ok) throw new Error("Failed to load robots");
  return res.json();
}

async function robotError(res: Response, fallback: string): Promise<Error> {
  try {
    const body = await res.json();
    const code = body?.error?.code as string | undefined;
    if (code === "ROBOT_ALREADY_EXISTS") return new Error("Bu marka/model/varyant zaten kayıtlı.");
    if (code === "ROBOT_NOT_SIM_COMPATIBLE")
      return new Error("Bu robot simülatörle uyumlu değil (sürüş tipi veya gövde yarıçapı).");
    if (code === "ROBOT_BUILTIN_READONLY")
      return new Error("Hazır katalog robotları değiştirilemez; kopyasını yeni robot olarak ekleyin.");
  } catch {
    /* fall through */
  }
  return new Error(fallback);
}

export async function createRobot(input: RobotProfileInput): Promise<RobotProfile> {
  const res = await apiFetch(`${API_BASE}/api/robots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await robotError(res, "Robot eklenemedi");
  return res.json();
}

export async function updateRobot(robotId: string, input: RobotProfileInput): Promise<RobotProfile> {
  const res = await apiFetch(`${API_BASE}/api/robots/${robotId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await robotError(res, "Robot güncellenemedi");
  return res.json();
}

export async function deleteRobot(robotId: string): Promise<void> {
  const res = await apiFetch(`${API_BASE}/api/robots/${robotId}`, { method: "DELETE" });
  if (!res.ok) throw await robotError(res, "Robot silinemedi");
}

export async function applyRobotToScenario(
  robotId: string,
  scenario: ScenarioSpec
): Promise<ScenarioSpec> {
  const res = await apiFetch(`${API_BASE}/api/robots/${robotId}/apply-to-scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(scenario),
  });
  if (!res.ok) throw await robotError(res, "Robot teste uygulanamadı");
  return res.json();
}

export async function generateScenario(objective?: string): Promise<{
  scenario: ScenarioSpec;
  provenance: string;
}> {
  const res = await apiFetch(`${API_BASE}/api/scenarios/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ objective: objective || "crowded crossing with delayed sensing" }),
  });
  if (res.status === 503) throw new Error("META_PROVIDER_UNAVAILABLE");
  if (!res.ok) throw new Error("Failed to generate scenario");
  return res.json();
}

export async function createRun(
  scenario: ScenarioSpec,
  policy: PolicyConfig,
  localPolicy?: string | null
) {
  const res = await apiFetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, policy, local_policy: localPolicy || null }),
  });
  if (res.status === 403) throw new Error("Yerel politika sunucuda kapalı (RW_ALLOW_LOCAL_POLICY=off).");
  if (res.status === 404) throw new Error("Yerel politika dosyası bulunamadı.");
  if (!res.ok) throw new Error("Failed to queue simulation run");
  return res.json();
}

export async function fetchLocalPolicies(): Promise<LocalPolicyInfo> {
  const res = await apiFetch(`${API_BASE}/api/local-policies`);
  if (!res.ok) throw new Error("Failed to load local policies");
  return res.json();
}

export async function fetchJob(jobId: string) {
  const res = await apiFetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to poll job status");
  return res.json();
}

export async function fetchRun(runId: string): Promise<RunResult> {
  const res = await apiFetch(`${API_BASE}/api/runs/${runId}`);
  if (!res.ok) throw new Error("Failed to fetch run results");
  return res.json();
}

export async function fetchTelemetry(
  runId: string,
  offset = 0,
  limit = 600
): Promise<{ frames: TelemetryFrame[]; total: number; next_offset: number | null }> {
  const res = await apiFetch(`${API_BASE}/api/runs/${runId}/telemetry?offset=${offset}&limit=${limit}`);
  if (!res.ok) throw new Error("Failed to load telemetry frames");
  return res.json();
}

export async function fetchAllFrames(
  fetchPage: (offset: number, limit: number) => Promise<{ frames: TelemetryFrame[]; total: number; next_offset: number | null }>
): Promise<TelemetryFrame[]> {
  const all: TelemetryFrame[] = [];
  let offset = 0;
  for (;;) {
    const page = await fetchPage(offset, 2000);
    all.push(...page.frames);
    if (page.next_offset === null || page.frames.length === 0) break;
    offset = page.next_offset;
  }
  return all;
}

export async function investigateFailure(runId: string) {
  const res = await apiFetch(`${API_BASE}/api/failures/${runId}/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (res.status === 409) throw new Error("Bu çalıştırma başarısız olmadı; incelenecek hata yok.");
  if (!res.ok) throw new Error("Failed to execute failure investigation");
  return res.json();
}

export async function verifyFix(baselineRunId: string, candidatePolicy: PolicyConfig) {
  const res = await apiFetch(`${API_BASE}/api/fixes/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ baseline_run_id: baselineRunId, candidate_policy: candidatePolicy }),
  });
  if (!res.ok) throw new Error("Failed to submit verification job");
  return res.json();
}

export async function fetchVerification(verificationId: string): Promise<VerificationRecord> {
  const res = await apiFetch(`${API_BASE}/api/verifications/${verificationId}`);
  if (!res.ok) throw new Error("Failed to load verification record");
  return res.json();
}

export interface VerificationSummary {
  verification_id: string;
  verdict: VerificationRecord["verdict"];
  baseline_run_id: string;
  created_at: string;
  completed_at: string | null;
}

export async function fetchVerifications(limit = 10): Promise<VerificationSummary[]> {
  const res = await apiFetch(`${API_BASE}/api/verifications?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to load verification history");
  return res.json();
}

export async function fetchPolicyProfiles(): Promise<PolicyProfile[]> {
  const res = await apiFetch(`${API_BASE}/api/policy-profiles`);
  if (!res.ok) throw new Error("Failed to load policy profiles");
  return res.json();
}

export async function createPolicyProfile(input: PolicyProfileInput): Promise<PolicyProfile> {
  const res = await apiFetch(`${API_BASE}/api/policy-profiles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (res.status === 409) throw new Error("Bu isimde bir profil zaten var.");
  if (!res.ok) throw new Error("Profil kaydedilemedi");
  return res.json();
}

export async function deletePolicyProfile(profileId: string): Promise<void> {
  const res = await apiFetch(`${API_BASE}/api/policy-profiles/${profileId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Profil silinemedi");
}

export async function createBattery(
  robotId: string,
  policy: PolicyConfig,
  scenarioIds?: string[],
  localPolicy?: string | null
): Promise<{ job_id: string; result_id: string; status: string }> {
  const res = await apiFetch(`${API_BASE}/api/batteries`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      robot_id: robotId,
      policy,
      scenario_ids: scenarioIds ?? [],
      local_policy: localPolicy || null,
    }),
  });
  if (res.status === 403) throw new Error("Yerel politika sunucuda kapalı (RW_ALLOW_LOCAL_POLICY=off).");
  if (res.status === 422) throw new Error("Bu robot veya senaryo bataryada çalıştırılamaz.");
  if (!res.ok) throw new Error("Batarya başlatılamadı");
  return res.json();
}

export async function fetchBattery(batteryId: string): Promise<BatteryResult> {
  const res = await apiFetch(`${API_BASE}/api/batteries/${batteryId}`);
  if (!res.ok) throw new Error("Karne yüklenemedi");
  return res.json();
}

export async function fetchBatteries(limit = 5): Promise<BatteryResult[]> {
  const res = await apiFetch(`${API_BASE}/api/batteries?limit=${limit}`);
  if (!res.ok) throw new Error("Karne geçmişi yüklenemedi");
  return res.json();
}

export function batteryReportUrl(batteryId: string): string {
  return `${API_BASE}/api/batteries/${batteryId}/report.md`;
}

export async function downloadBatteryReport(batteryId: string): Promise<void> {
  let lang = "tr";
  try {
    lang = localStorage.getItem("rw_locale") === "en" ? "en" : "tr";
  } catch {
    /* default tr */
  }
  const res = await apiFetch(`${batteryReportUrl(batteryId)}?lang=${lang}`);
  if (!res.ok) throw new Error("Karne indirilemedi");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${batteryId}-karne.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export interface BatteryCompareEntry {
  scenario_id: string;
  title: string;
  status_a: string | null;
  status_b: string | null;
  clearance_a: number | null;
  clearance_b: number | null;
  outcome: "improved" | "worsened" | "same" | "only_a" | "only_b";
}

export async function compareBatteries(
  a: string,
  b: string
): Promise<{ a: BatteryResult; b: BatteryResult; entries: BatteryCompareEntry[]; summary_delta: Record<string, number> }> {
  const res = await apiFetch(`${API_BASE}/api/batteries/compare?a=${a}&b=${b}`);
  if (!res.ok) throw new Error("Karşılaştırma yapılamadı");
  return res.json();
}

export interface AdminApiKey {
  key_id: string;
  label: string;
  role_name: string;
  workspace_id: string;
  created_at: string;
  revoked_at: string | null;
}

export async function fetchAdminApiKeys(): Promise<AdminApiKey[]> {
  const res = await apiFetch(`${API_BASE}/api/admin/api-keys`);
  if (!res.ok) throw new Error("Anahtarlar yüklenemedi");
  return (await res.json()).keys;
}

export async function createAdminApiKey(
  label: string,
  role: string,
  workspaceId: string
): Promise<{ key_id: string; api_key: string }> {
  const res = await apiFetch(`${API_BASE}/api/admin/api-keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ label, role, workspace_id: workspaceId }),
  });
  if (!res.ok) throw new Error("Anahtar oluşturulamadı (admin gerekli)");
  return res.json();
}

export async function revokeAdminApiKey(keyId: string): Promise<void> {
  const res = await apiFetch(`${API_BASE}/api/admin/api-keys/${keyId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Anahtar iptal edilemedi");
}

export async function fetchAudit(limit = 30): Promise<Array<Record<string, unknown>>> {
  const res = await apiFetch(`${API_BASE}/api/audit?limit=${limit}`);
  if (!res.ok) throw new Error("Denetim kaydı yüklenemedi (admin gerekli)");
  return (await res.json()).entries;
}

export async function fetchMetrics(): Promise<Record<string, unknown>> {
  const res = await apiFetch(`${API_BASE}/api/metrics`);
  if (!res.ok) throw new Error("Metrikler yüklenemedi");
  return res.json();
}

export async function createBackup(): Promise<{ file: string; sha256: string; bytes: number }> {
  const res = await apiFetch(`${API_BASE}/api/admin/backup`, { method: "POST" });
  if (!res.ok) throw new Error("Yedek alınamadı (admin gerekli)");
  return res.json();
}

export interface BatterySchedule {
  schedule_id: string;
  name: string;
  robot_id: string;
  interval_minutes: number;
  next_run_at: string;
  last_run_at: string | null;
  enabled: boolean;
  created_at: string;
}

export async function fetchSchedules(): Promise<BatterySchedule[]> {
  const res = await apiFetch(`${API_BASE}/api/batteries/schedules`);
  if (!res.ok) throw new Error("Zamanlamalar yüklenemedi");
  return res.json();
}

export async function createSchedule(payload: {
  name: string;
  robot_id: string;
  policy: PolicyConfig;
  scenario_ids: string[];
  interval_minutes: number;
}): Promise<BatterySchedule> {
  const res = await apiFetch(`${API_BASE}/api/batteries/schedules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Zamanlama oluşturulamadı");
  return res.json();
}

export async function deleteSchedule(scheduleId: string): Promise<void> {
  const res = await apiFetch(`${API_BASE}/api/batteries/schedules/${scheduleId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Zamanlama silinemedi");
}

export interface BatteryTrendPoint {
  battery_id: string;
  robot_id: string;
  robot_label: string;
  created_at: string;
  passed: number;
  total: number;
  pass_rate: number;
  collisions: number;
  near_misses: number;
}

export async function fetchBatteryTrend(robotId?: string): Promise<BatteryTrendPoint[]> {
  const qs = robotId ? `?robot_id=${encodeURIComponent(robotId)}` : "";
  const res = await apiFetch(`${API_BASE}/api/batteries/trend${qs}`);
  if (!res.ok) throw new Error("Trend yüklenemedi");
  return res.json();
}

export async function runFleet(
  robotIds: string[],
  policy: PolicyConfig,
  scenarioIds?: string[]
): Promise<{ jobs: Array<{ robot_id: string; job_id: string; battery_id: string }>; skipped: Array<{ robot_id: string; reason: string }> }> {
  const res = await apiFetch(`${API_BASE}/api/batteries/fleet`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ robot_ids: robotIds, policy, scenario_ids: scenarioIds ?? [] }),
  });
  if (!res.ok) throw new Error("Filo bataryası başlatılamadı");
  return res.json();
}

export async function convertMapToScenario(
  name: string,
  gridText: string,
  cellSizeM: number
): Promise<{ scenario: ScenarioSpec; warnings: string[] }> {
  const res = await apiFetch(`${API_BASE}/api/maps/scenario`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, grid_text: gridText, cell_size_m: cellSizeM }),
  });
  if (res.status === 422) {
    try {
      const body = await res.json();
      throw new Error(body?.error?.message || "Harita senaryoya çevrilemedi");
    } catch (e) {
      if (e instanceof Error && e.message !== "Harita senaryoya çevrilemedi") throw e;
      throw new Error("Harita senaryoya çevrilemedi (boyut veya engel yerleşimi uygun değil)");
    }
  }
  if (!res.ok) throw new Error("Harita senaryoya çevrilemedi");
  return res.json();
}

export async function importTelemetry(payload: {
  name: string;
  robot_label: string;
  format: "csv" | "json";
  content: string;
  goal?: { x_m: number; y_m: number } | null;
}): Promise<ImportResult> {
  const res = await apiFetch(`${API_BASE}/api/imports/telemetry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (res.status === 422) throw new Error("Dosya okunamadı. CSV başlıkları: t_s,x_m,y_m,yaw_rad,min_obstacle_distance_m");
  if (!res.ok) throw new Error("Gerçek sürüş yüklenemedi");
  return res.json();
}

export async function fetchCandidateTelemetry(
  verificationId: string,
  offset = 0,
  limit = 600
): Promise<{ frames: TelemetryFrame[]; total: number; next_offset: number | null }> {
  const res = await apiFetch(
    `${API_BASE}/api/verifications/${verificationId}/candidate-telemetry?offset=${offset}&limit=${limit}`
  );
  if (res.status === 404) throw new Error("CANDIDATE_REPLAY_MISSING");
  if (!res.ok) throw new Error("Failed to load candidate telemetry");
  return res.json();
}
