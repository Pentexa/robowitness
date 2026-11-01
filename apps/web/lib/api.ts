import {
  PolicyConfig,
  RobotProfile,
  RobotProfileInput,
  ScenarioCatalogEntry,
  ScenarioSpec,
  TelemetryFrame,
  VerificationRecord,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_RW_API_URL || "http://localhost:8000";

export const API_BASE_URL = API_BASE;

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export async function fetchReferenceScenarios(): Promise<ScenarioSpec[]> {
  const res = await fetch(`${API_BASE}/api/scenarios/reference`);
  if (!res.ok) throw new Error("Failed to load reference scenarios");
  return res.json();
}

export async function fetchScenarioLibrary(): Promise<ScenarioCatalogEntry[]> {
  const res = await fetch(`${API_BASE}/api/scenarios/library`);
  if (!res.ok) throw new Error("Failed to load scenario library");
  return res.json();
}

export async function fetchRobots(): Promise<RobotProfile[]> {
  const res = await fetch(`${API_BASE}/api/robots`);
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
  const res = await fetch(`${API_BASE}/api/robots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await robotError(res, "Robot eklenemedi");
  return res.json();
}

export async function updateRobot(robotId: string, input: RobotProfileInput): Promise<RobotProfile> {
  const res = await fetch(`${API_BASE}/api/robots/${robotId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw await robotError(res, "Robot güncellenemedi");
  return res.json();
}

export async function deleteRobot(robotId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/robots/${robotId}`, { method: "DELETE" });
  if (!res.ok) throw await robotError(res, "Robot silinemedi");
}

export async function applyRobotToScenario(
  robotId: string,
  scenario: ScenarioSpec
): Promise<ScenarioSpec> {
  const res = await fetch(`${API_BASE}/api/robots/${robotId}/apply-to-scenario`, {
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
  const res = await fetch(`${API_BASE}/api/scenarios/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ objective: objective || "crowded crossing with delayed sensing" }),
  });
  if (res.status === 503) throw new Error("META_PROVIDER_UNAVAILABLE");
  if (!res.ok) throw new Error("Failed to generate scenario");
  return res.json();
}

export async function createRun(scenario: ScenarioSpec, policy: PolicyConfig) {
  const res = await fetch(`${API_BASE}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scenario, policy }),
  });
  if (!res.ok) throw new Error("Failed to queue simulation run");
  return res.json();
}

export async function fetchJob(jobId: string) {
  const res = await fetch(`${API_BASE}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to poll job status");
  return res.json();
}

export async function fetchRun(runId: string) {
  const res = await fetch(`${API_BASE}/api/runs/${runId}`);
  if (!res.ok) throw new Error("Failed to fetch run results");
  return res.json();
}

export async function fetchTelemetry(
  runId: string,
  offset = 0,
  limit = 600
): Promise<{ frames: TelemetryFrame[]; total: number; next_offset: number | null }> {
  const res = await fetch(`${API_BASE}/api/runs/${runId}/telemetry?offset=${offset}&limit=${limit}`);
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
  const res = await fetch(`${API_BASE}/api/failures/${runId}/investigate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error("Failed to execute failure investigation");
  return res.json();
}

export async function verifyFix(baselineRunId: string, candidatePolicy: PolicyConfig) {
  const res = await fetch(`${API_BASE}/api/fixes/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ baseline_run_id: baselineRunId, candidate_policy: candidatePolicy }),
  });
  if (!res.ok) throw new Error("Failed to submit verification job");
  return res.json();
}

export async function fetchVerification(verificationId: string): Promise<VerificationRecord> {
  const res = await fetch(`${API_BASE}/api/verifications/${verificationId}`);
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
  const res = await fetch(`${API_BASE}/api/verifications?limit=${limit}`);
  if (!res.ok) throw new Error("Failed to load verification history");
  return res.json();
}

export async function fetchCandidateTelemetry(
  verificationId: string,
  offset = 0,
  limit = 600
): Promise<{ frames: TelemetryFrame[]; total: number; next_offset: number | null }> {
  const res = await fetch(
    `${API_BASE}/api/verifications/${verificationId}/candidate-telemetry?offset=${offset}&limit=${limit}`
  );
  if (res.status === 404) throw new Error("CANDIDATE_REPLAY_MISSING");
  if (!res.ok) throw new Error("Failed to load candidate telemetry");
  return res.json();
}
