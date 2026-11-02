"use client";

import React, { useEffect, useState } from "react";
import { HelpCircle, X } from "lucide-react";
import { ComparisonReplay } from "../components/ComparisonReplay";
import { EvidencePanel } from "../components/EvidencePanel";
import { FailureAnalysis } from "../components/FailureAnalysis";
import { FixComparison } from "../components/FixComparison";
import { ReplayControls } from "../components/ReplayControls";
import { AdminPanel } from "../components/AdminPanel";
import { BatteryPanel } from "../components/BatteryPanel";
import { useLocale } from "../lib/i18n";
import { LocalPolicyPanel } from "../components/LocalPolicyPanel";
import { MapImport } from "../components/MapImport";
import { PolicyProfiles } from "../components/PolicyProfiles";
import { RobotPanel } from "../components/RobotPanel";
import { RunVerdict } from "../components/RunVerdict";
import { ScenarioLibrary } from "../components/ScenarioLibrary";
import { ScenarioPanel } from "../components/ScenarioPanel";
import { SimulationCanvas } from "../components/SimulationCanvas";
import { SimulationCanvas3D } from "../components/SimulationCanvas3D";
import { Timeline } from "../components/Timeline";
import { VerificationDecision } from "../components/VerificationDecision";
import { VerificationHistory } from "../components/VerificationHistory";
import {
  createRun,
  fetchAllFrames,
  fetchHealth,
  fetchJob,
  fetchLocalPolicies,
  fetchReferenceScenarios,
  fetchRun,
  fetchScenarioLibrary,
  fetchTelemetry,
  fetchVerification,
  fetchVerifications,
  generateScenario,
  investigateFailure,
  verifyFix,
  type VerificationSummary,
} from "../lib/api";
import {
  InvestigationResponse,
  LocalPolicyInfo,
  PolicyConfig,
  PolicyPatch,
  RunResult,
  ScenarioCatalogEntry,
  ScenarioSpec,
  TelemetryFrame,
  VerificationRecord,
} from "../lib/types";

const DEFAULT_BASELINE_POLICY: PolicyConfig = {
  schema_version: "1.0",
  id: "baseline-v1",
  max_speed_mps: 0.75,
  safe_distance_m: 0.3,
  reaction_margin_m: 0.05,
  brake_gain: 1.5,
  obstacle_prediction_horizon_s: 0.0,
};

const DEFAULT_CANDIDATE_POLICY: PolicyConfig = {
  schema_version: "1.0",
  id: "candidate-v1",
  max_speed_mps: 0.45,
  safe_distance_m: 0.85,
  reaction_margin_m: 0.15,
  brake_gain: 3.0,
  obstacle_prediction_horizon_s: 0.6,
};

type PanelId = "test" | "hata" | "duzeltme" | "sonuc" | "karne" | "yonetim";

const STEPS: Array<{ panel: PanelId; name: string; desc: string }> = [
  { panel: "test", name: "Testi çalıştır", desc: "Robotu eski ayarlarla bir kez çalıştırın." },
  { panel: "hata", name: "İnceleme", desc: "Kaza veya yakın geçiş neden oldu, öğrenin." },
  { panel: "duzeltme", name: "Düzeltmeyi dene", desc: "Yeni ayarları yazın ve test edin." },
  { panel: "sonuc", name: "Sonucu gör", desc: "Kabul mü, ret mi? Raporu indirin." },
];

export default function DashboardPage() {
  const { locale, setLocale, t } = useLocale();
  const [scenario, setScenario] = useState<ScenarioSpec | null>(null);
  const [library, setLibrary] = useState<ScenarioCatalogEntry[]>([]);
  const [appliedRobotLabel, setAppliedRobotLabel] = useState<string | null>(null);
  const [scenarioProvenance, setScenarioProvenance] = useState<string>("BUNDLED_REFERENCE");
  const [baselinePolicy] = useState<PolicyConfig>(DEFAULT_BASELINE_POLICY);
  const [candidatePolicy, setCandidatePolicy] = useState<PolicyConfig>(DEFAULT_CANDIDATE_POLICY);
  const [viewMode, setViewMode] = useState<"2d" | "3d">("2d");
  const [activePanel, setActivePanel] = useState<PanelId>("test");
  const [helpOpen, setHelpOpen] = useState<boolean>(false);

  const [frames, setFrames] = useState<TelemetryFrame[]>([]);
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(1.0);

  const [isRunningBaseline, setIsRunningBaseline] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [localPolicyInfo, setLocalPolicyInfo] = useState<LocalPolicyInfo | null>(null);
  const [selectedLocalPolicy, setSelectedLocalPolicy] = useState<string>("");
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [verification, setVerification] = useState<VerificationRecord | null>(null);
  const [history, setHistory] = useState<VerificationSummary[]>([]);
  const [provenance, setProvenance] = useState<string>("OFFLINE_REFERENCE");
  const [metaModel, setMetaModel] = useState<string | null>(null);
  const [backendUp, setBackendUp] = useState<boolean>(false);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setBackendUp(h.status === "healthy");
        setProvenance(h.ai_mode === "live" ? "LIVE_META" : "OFFLINE_REFERENCE");
        setMetaModel(typeof h.meta_model === "string" && h.meta_model ? h.meta_model : null);
      })
      .catch(() => setBackendUp(false));

    fetchReferenceScenarios()
      .then((scenarios) => {
        // Only as the initial value: never clobber a scenario the user (or a
        // restored flow) has already picked while this request was in flight.
        if (scenarios.length > 0) setScenario((prev) => prev ?? scenarios[0]);
      })
      .catch((err) => console.error("Could not load scenarios:", err));

    fetchVerifications(10)
      .then((h) => setHistory(h))
      .catch(() => console.warn("Verification history unavailable"));

    fetchScenarioLibrary()
      .then((entries) => setLibrary(entries))
      .catch(() => console.warn("Scenario library unavailable"));

    fetchLocalPolicies()
      .then((info) => setLocalPolicyInfo(info))
      .catch(() => console.warn("Local policies unavailable"));

    try {
      const savedRunId = localStorage.getItem("rw_run_id");
      const savedVerifId = localStorage.getItem("rw_verification_id");
      if (savedRunId) {
        setActiveRunId(savedRunId);
        fetchRun(savedRunId)
          .then((r) => setRunResult(r))
          .catch(() => {
            // Stale saved id (artifacts were cleaned): forget it instead of
            // failing the same restore on every page load.
            try {
              localStorage.removeItem("rw_run_id");
            } catch {
              /* ignore */
            }
            setActiveRunId(null);
          });
        fetchAllFrames((o, l) => fetchTelemetry(savedRunId, o, l))
          .then((all) => setFrames(all))
          .catch(() => console.warn("Saved run telemetry unavailable"));
      }
      if (savedVerifId) {
        fetchVerification(savedVerifId)
          .then((record) => setVerification(record))
          .catch(() => console.warn("Saved verification record unavailable"));
      }
    } catch {
      console.warn("localStorage unavailable; state starts empty");
    }
  }, []);

  useEffect(() => {
    if (!isPlaying || frames.length === 0) return;
    const timer = setInterval(() => {
      setCurrentFrameIndex((prev) => {
        if (prev >= frames.length - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 1000 / 60 / speed);
    return () => clearInterval(timer);
  }, [isPlaying, frames, speed]);

  // Kullanıcı hep sıradaki adımın sekmesinde olsun.
  useEffect(() => {
    if (verification) setActivePanel("sonuc");
    else if (investigation) setActivePanel("duzeltme");
  }, [verification, investigation]);

  const resetRunState = (keepScenario: boolean) => {
    if (!keepScenario) {
      setActiveRunId(null);
    }
    setVerification(null);
    setInvestigation(null);
    setRunResult(null);
    setFrames([]);
    setCurrentFrameIndex(0);
    setIsPlaying(false);
    try {
      localStorage.removeItem("rw_run_id");
      localStorage.removeItem("rw_verification_id");
    } catch {
      console.warn("localStorage unavailable");
    }
  };

  const handleSelectReference = () => {
    fetchReferenceScenarios().then((s) => {
      if (s.length === 0) return;
      setScenario(s[0]);
      setScenarioProvenance("BUNDLED_REFERENCE");
      setAppliedRobotLabel(null);
      resetRunState(false);
      setActivePanel("test");
    });
  };

  const handleSelectLibrary = (entry: ScenarioCatalogEntry) => {
    setScenario(entry.scenario);
    setScenarioProvenance("SCENARIO_LIBRARY");
    setAppliedRobotLabel(null);
    resetRunState(false);
    setActivePanel("test");
  };

  const handleRobotApplied = (applied: ScenarioSpec, robotLabel: string) => {
    setScenario(applied);
    setScenarioProvenance("ROBOT_PROFILE_APPLIED");
    setAppliedRobotLabel(robotLabel);
    resetRunState(false);
    setActivePanel("test");
  };

  const handleGenerateAI = async () => {
    setIsGenerating(true);
    setGenerationError(null);
    try {
      const gen = await generateScenario("crowded crossing with delayed sensing");
      setScenario(gen.scenario);
      setScenarioProvenance(gen.provenance);
      setAppliedRobotLabel(null);
      resetRunState(false);
      setActivePanel("test");
    } catch (e) {
      setGenerationError(e instanceof Error ? e.message : t("Yeni test oluşturulamadı"));
    } finally {
      setIsGenerating(false);
    }
  };

  const handleRunBaseline = async () => {
    if (!scenario) return;
    setIsRunningBaseline(true);
    setIsPlaying(false);
    setCurrentFrameIndex(0);
    setInvestigation(null);
    setVerification(null);
    setRunResult(null);
    try {
      localStorage.removeItem("rw_verification_id");
    } catch {
      console.warn("localStorage unavailable");
    }
    try {
      const runJob = await createRun(scenario, baselinePolicy, selectedLocalPolicy || null);
      const pollInterval = setInterval(async () => {
        try {
          const job = await fetchJob(runJob.job_id);
          if (job.status === "completed") {
            clearInterval(pollInterval);
            setIsRunningBaseline(false);
            setActiveRunId(runJob.result_id);
            try {
              localStorage.setItem("rw_run_id", runJob.result_id);
            } catch {
              console.warn("localStorage unavailable");
            }
            const all = await fetchAllFrames((o, l) => fetchTelemetry(runJob.result_id, o, l));
            setFrames(all);
            setIsPlaying(true);
            // Independent oracle decides: only a FAIL goes to failure analysis.
            // A clean (PASS) run stays here and shows its verdict instead.
            const result = await fetchRun(runJob.result_id).catch(() => null);
            setRunResult(result);
            setActivePanel(result?.oracle_status === "FAIL" ? "hata" : "test");
          } else if (job.status === "failed" || job.status === "cancelled") {
            clearInterval(pollInterval);
            setIsRunningBaseline(false);
          }
        } catch (e) {
          clearInterval(pollInterval);
          setIsRunningBaseline(false);
          console.error(e);
        }
      }, 750);
    } catch (e) {
      setIsRunningBaseline(false);
      console.error(e);
    }
  };

  const handleLoadBatteryRun = async (runId: string) => {
    try {
      setActiveRunId(runId);
      setVerification(null);
      setInvestigation(null);
      setRunResult(await fetchRun(runId).catch(() => null));
      const all = await fetchAllFrames((o, l) => fetchTelemetry(runId, o, l));
      setFrames(all);
      setCurrentFrameIndex(0);
      setIsPlaying(false);
      setActivePanel("test");
      try {
        localStorage.setItem("rw_run_id", runId);
        localStorage.removeItem("rw_verification_id");
      } catch {
        console.warn("localStorage unavailable");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleInvestigate = async () => {
    if (!activeRunId) return;
    const result: InvestigationResponse = await investigateFailure(activeRunId);
    setInvestigation(result);
    setProvenance(result.provenance);
  };

  const handleApplyPatch = (patch: PolicyPatch) => {
    setCandidatePolicy((prev) => ({
      ...prev,
      ...(patch.max_speed_mps !== undefined ? { max_speed_mps: patch.max_speed_mps } : {}),
      ...(patch.safe_distance_m !== undefined ? { safe_distance_m: patch.safe_distance_m } : {}),
      ...(patch.reaction_margin_m !== undefined ? { reaction_margin_m: patch.reaction_margin_m } : {}),
      ...(patch.brake_gain !== undefined ? { brake_gain: patch.brake_gain } : {}),
      ...(patch.obstacle_prediction_horizon_s !== undefined
        ? { obstacle_prediction_horizon_s: patch.obstacle_prediction_horizon_s }
        : {}),
    }));
    setActivePanel("duzeltme");
  };

  const handleVerify = async () => {
    if (!activeRunId) return;
    setIsVerifying(true);
    setActivePanel("sonuc");
    try {
      const verifJob = await verifyFix(activeRunId, candidatePolicy);
      const pollInterval = setInterval(async () => {
        try {
          const job = await fetchJob(verifJob.job_id);
          if (job.status === "completed") {
            clearInterval(pollInterval);
            setIsVerifying(false);
            const record = await fetchVerification(verifJob.result_id);
            setVerification(record);
            setHistory(await fetchVerifications(10).catch(() => [] as VerificationSummary[]));
            try {
              localStorage.setItem("rw_verification_id", verifJob.result_id);
            } catch {
              console.warn("localStorage unavailable");
            }
          } else if (job.status === "failed" || job.status === "cancelled") {
            clearInterval(pollInterval);
            setIsVerifying(false);
          }
        } catch (e) {
          clearInterval(pollInterval);
          setIsVerifying(false);
          console.error(e);
        }
      }, 1000);
    } catch (e) {
      setIsVerifying(false);
      console.error(e);
    }
  };

  const handleSelectHistory = async (verificationId: string) => {
    if (!verificationId) {
      setVerification(null);
      try {
        localStorage.removeItem("rw_verification_id");
      } catch {
        console.warn("localStorage unavailable");
      }
      return;
    }
    try {
      const record = await fetchVerification(verificationId);
      setVerification(record);
      setActiveRunId(record.baseline_run_id);
      setRunResult(await fetchRun(record.baseline_run_id).catch(() => null));
      setInvestigation(null);
      const all = await fetchAllFrames((o, l) => fetchTelemetry(record.baseline_run_id, o, l));
      setFrames(all);
      setCurrentFrameIndex(0);
      setIsPlaying(false);
      try {
        localStorage.setItem("rw_verification_id", verificationId);
        localStorage.setItem("rw_run_id", record.baseline_run_id);
      } catch {
        console.warn("localStorage unavailable");
      }
    } catch (e) {
      console.error(e);
    }
  };

  const currentSimTime = frames[currentFrameIndex]?.sim_time_s ?? 0.0;
  const totalDuration = frames[frames.length - 1]?.sim_time_s ?? 0.0;

  // Adım, bağımsız kontrolün (oracle) kararına göre ilerler: yalnızca FAIL
  // çalıştırma "Hatayı incele" adımına geçer. Kazasız (PASS) çalıştırmada
  // incelenecek hata yoktur; kullanıcı yeni senaryo/robot seçip tekrar dener.
  const runFailed = runResult?.oracle_status === "FAIL";
  // Near-miss: hedefe ulaştı, çarpışma yok, ama güvenli mesafe aşıldı.
  const nearMiss =
    runResult !== null &&
    runResult.oracle_status === "FAIL" &&
    !runResult.metrics.collision_detected &&
    runResult.metrics.goal_reached;
  const currentStep = verification ? 3 : investigation ? 2 : runFailed ? 1 : 0;
  const busy = isRunningBaseline || isVerifying || isGenerating;
  const nextText = runResult && !verification && !investigation
    ? runResult.oracle_status === "PASS"
      ? t("Test kazasız tamamlandı. Yeni bir senaryo veya robot seçip tekrar çalıştırabilirsiniz.")
      : runResult.oracle_status === "FAIL"
        ? nearMiss
          ? t("Çarpışma olmadı ama robot engele {m} m yaklaştı (güvenli sınır: {s} m). Bu yüzden test başarısız sayıldı; yakın geçişi inceleyebilirsiniz.")
              .replace("{m}", String(runResult.metrics.min_clearance_m))
              .replace("{s}", String(scenario?.oracle.min_clearance_m ?? 0.25))
          : t("Çalıştırma başarısız oldu. Tekrarı izleyip incelemeyi açabilirsiniz.")
        : t("Sonuç belirlenemedi. Tekrarı izleyip yeniden çalıştırmayı deneyin.")
    : [
        t("Hazır test yüklü. Robotu eski ayarlarla bir kez çalıştırın."),
        t("Çalıştırma bitti. Aşağıdan tekrarını izleyebilir, sonra hatayı inceleyebilirsiniz."),
        t("Yeni ayarları kaydırıcılarla değiştirin (ya da öneriyi kullandınız), sonra test edin."),
        t("Sonuç hazır. Kararı okuyun, isterseniz mühürlü raporu indirin."),
      ][currentStep];

  return (
    <div className="rw-app">
      {/* Program başlık çubuğu */}
      <div className="rw-titlebar">
        <div className="rw-titlebar-left">
          <img className="rw-mark" src="/rw-mark.svg" alt="" draggable={false} />
          <span className="rw-appname">
            RoboWitness <span className="dim">— {t("Robot Test Programı")}</span>
          </span>
          <span
            className={`rw-badge ${provenance === "LIVE_META" ? "is-live" : "is-dim"}`}
            title={
              provenance === "LIVE_META"
                ? t("Senaryo üretimi ve hata incelemesi Meta AI ile canlı çalışıyor")
                : t("Meta AI anahtarı yok: çevrimdışı yedek mod")
            }
          >
            Meta AI{provenance === "LIVE_META" ? ` · ${metaModel ?? t("Canlı")}` : ` · ${t("Çevrimdışı")}`}
          </span>
        </div>
        <div className="rw-row">
          <input
            id="input-api-key"
            className="rw-input"
            type="password"
            placeholder={t("API anahtarı (varsa)")}
            style={{ width: 160 }}
            defaultValue={typeof window !== "undefined" ? (localStorage.getItem("rw_api_key") ?? "") : ""}
            onBlur={(e) => {
              try {
                if (e.target.value) localStorage.setItem("rw_api_key", e.target.value);
                else localStorage.removeItem("rw_api_key");
              } catch {
                console.warn("localStorage unavailable");
              }
            }}
            title={t("Sunucu RW_API_KEYS ile korunuyorsa anahtarınızı yazın; tarayıcıda saklanır")}
          />
          <input
            id="input-jwt"
            className="rw-input"
            type="password"
            placeholder={t("JWT (varsa)")}
            style={{ width: 130 }}
            defaultValue={typeof window !== "undefined" ? (localStorage.getItem("rw_jwt") ?? "") : ""}
            onBlur={(e) => {
              try {
                if (e.target.value) localStorage.setItem("rw_jwt", e.target.value);
                else localStorage.removeItem("rw_jwt");
              } catch {
                console.warn("localStorage unavailable");
              }
            }}
            title={t("OIDC/JWT erişim belirteci (Authorization: Bearer); tarayıcıda saklanır")}
          />
          <input
            id="input-workspace"
            className="rw-input"
            placeholder={t("Çalışma alanı")}
            style={{ width: 120 }}
            defaultValue={typeof window !== "undefined" ? (localStorage.getItem("rw_workspace") ?? "") : ""}
            onBlur={(e) => {
              try {
                if (e.target.value) localStorage.setItem("rw_workspace", e.target.value);
                else localStorage.removeItem("rw_workspace");
                window.location.reload();
              } catch {
                console.warn("localStorage unavailable");
              }
            }}
            title={t("Çalışma alanı (workspace): verileriniz bu alanda izole edilir; değişince sayfa yenilenir")}
          />
          <div className="rw-btn-group" role="group" aria-label="Language / Dil">
            <button
              id="btn-lang-en"
              className={`rw-btn rw-btn-sm ${locale === "en" ? "rw-btn-primary" : "rw-btn-ghost"}`}
              onClick={() => setLocale("en")}
            >
              EN
            </button>
            <button
              id="btn-lang-tr"
              className={`rw-btn rw-btn-sm ${locale === "tr" ? "rw-btn-primary" : "rw-btn-ghost"}`}
              onClick={() => setLocale("tr")}
            >
              TR
            </button>
          </div>
          <button className="rw-btn rw-btn-ghost rw-btn-sm" id="btn-help" onClick={() => setHelpOpen(true)}>
            <HelpCircle size={14} /> {t("Yardım")}
          </button>
        </div>
      </div>

      {/* Araç çubuğu: sıradaki adım */}
      <div className="rw-toolbar">
        <div className="rw-next" role="status">
          <strong>{busy ? t("Çalışıyor…") : `${t("Sıradaki adım")} (${currentStep + 1}/4):`}</strong>
          <span>{busy ? t("Lütfen bekleyin, pencereyi kapatmayın.") : nextText}</span>
        </div>
        <div className="rw-toolbar-spacer" />
        {currentStep === 0 && (
          <button id="btn-toolbar-run" className="rw-btn rw-btn-primary" onClick={handleRunBaseline} disabled={busy || !scenario}>
            ▶ {t("Robotu Çalıştır")}
          </button>
        )}
        {currentStep === 1 && (
          <button
            id="btn-toolbar-investigate"
            className="rw-btn rw-btn-primary"
            disabled={busy}
            onClick={() => {
              setActivePanel("hata");
              handleInvestigate().catch(() => console.error("Investigation failed"));
            }}
          >
            {nearMiss ? t("Yakın Geçişi İncele") : t("Hatayı İncele")}
          </button>
        )}
        {currentStep === 2 && (
          <button id="btn-toolbar-verify" className="rw-btn rw-btn-primary" onClick={handleVerify} disabled={busy}>
            {t("Düzeltmeyi Test Et")}
          </button>
        )}
        {currentStep === 3 && (
          <button id="btn-toolbar-result" className="rw-btn rw-btn-primary" onClick={() => setActivePanel("sonuc")}>
            {t("Sonucu Gör")}
          </button>
        )}
      </div>

      {/* Çalışma alanı */}
      <main className="rw-workspace">
        {/* Simülasyon görünümü */}
        <section className="rw-viewport-area" aria-label="Test alanı">
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {runResult && (
              <RunVerdict result={runResult} minClearanceLimitM={scenario?.oracle.min_clearance_m} />
            )}
            <div className="rw-card">
              <div className="rw-card-head">
                <h2 className="rw-card-title">{t("Test Alanı")}</h2>
                <div className="rw-row">
                  <div className="rw-btn-group" role="group" aria-label="View">
                    <button
                      id="btn-view-2d"
                      className={`rw-btn rw-btn-sm ${viewMode === "2d" ? "rw-btn-primary" : "rw-btn-ghost"}`}
                      onClick={() => setViewMode("2d")}
                    >
                      {t("2B Üstten")}
                    </button>
                    <button
                      id="btn-view-3d"
                      className={`rw-btn rw-btn-sm ${viewMode === "3d" ? "rw-btn-primary" : "rw-btn-ghost"}`}
                      onClick={() => setViewMode("3d")}
                    >
                      3B
                    </button>
                  </div>
                  <span className="rw-badge mono">
                    {scenario ? `${scenario.obstacles.length} ${t("ENGEL")}` : "—"}
                    {frames.length > 0 ? ` · ${frames.length} ${t("ADIM")}` : ""}
                  </span>
                </div>
              </div>
              <div className="rw-card-body">
                {frames.length === 0 && (
                  <p className="rw-summary">{t("Başlamak için sağdan senaryo ve robot seçip “Robotu Çalıştır”a basın.")}</p>
                )}
                {viewMode === "2d" ? (
                  <SimulationCanvas scenario={scenario} frames={frames} currentFrameIndex={currentFrameIndex} />
                ) : (
                  <SimulationCanvas3D scenario={scenario} frames={frames} currentFrameIndex={currentFrameIndex} />
                )}
                <div className="rw-legend" aria-label="Legend">
                  <span><b>● {t("Beyaz top:")}</b> {t("Robot")}</span>
                  <span><b>◎ {t("Kesikli halka:")}</b> {t("Hedef")}</span>
                  <span><b>○ {t("Gri halkalar:")}</b> {t("Engeller")}</span>
                  <span><b>— {t("Çizgi:")}</b> {t("Robotun yolu")}</span>
                  {frames.length > 0 && scenario && (
                    <span>
                      <b>{t("Engel mesafesi:")}</b>{" "}
                      <span className="mono">{frames[currentFrameIndex]?.clearance_m.toFixed(2)} m</span>
                      {frames[currentFrameIndex] &&
                      frames[currentFrameIndex].clearance_m < scenario.oracle.min_clearance_m ? (
                        <span className="rw-badge is-fail">
                          {t("Güvenli sınırın altında")} ({scenario.oracle.min_clearance_m} m)
                        </span>
                      ) : (
                        <span> ({t("güvenli sınır:")} {scenario.oracle.min_clearance_m} m)</span>
                      )}
                    </span>
                  )}
                </div>
                <ReplayControls
                  isPlaying={isPlaying}
                  onTogglePlay={() => setIsPlaying(!isPlaying)}
                  onReset={() => {
                    setIsPlaying(false);
                    setCurrentFrameIndex(0);
                  }}
                  onStepForward={() => {
                    setIsPlaying(false);
                    setCurrentFrameIndex((p) => Math.min(frames.length - 1, p + 1));
                  }}
                  onStepBackward={() => {
                    setIsPlaying(false);
                    setCurrentFrameIndex((p) => Math.max(0, p - 1));
                  }}
                  speed={speed}
                  onSpeedChange={setSpeed}
                  currentSimTime={currentSimTime}
                  totalDuration={totalDuration}
                />
                <Timeline
                  frames={frames}
                  currentIndex={currentFrameIndex}
                  onSeek={(idx) => {
                    setIsPlaying(false);
                    setCurrentFrameIndex(idx);
                  }}
                />
              </div>
            </div>

            {verification && (
              <ComparisonReplay
                scenario={scenario}
                baselineRunId={verification.baseline_run_id}
                verificationId={verification.verification_id}
                gates={verification.gates}
              />
            )}
          </div>
        </section>

        {/* Sağ: sekmeli işlem paneli */}
        <aside className="rw-inspector" aria-label="İşlem paneli">
          <div className="rw-tabs" role="tablist" aria-label="İşlem sekmeleri">
            {STEPS.map((s, i) => (
              <button
                key={s.panel}
                role="tab"
                aria-selected={activePanel === s.panel}
                className={`rw-tab ${activePanel === s.panel ? "is-active" : ""}`}
                onClick={() => setActivePanel(s.panel)}
              >
                {i + 1}. {s.panel === "test" ? t("Test") : s.panel === "hata" ? t("İncele") : s.panel === "duzeltme" ? t("Düzeltme") : t("Sonuç")}
              </button>
            ))}
            <button
              role="tab"
              aria-selected={activePanel === "karne"}
              className={`rw-tab ${activePanel === "karne" ? "is-active" : ""}`}
              onClick={() => setActivePanel("karne")}
            >
              {t("Karne")}
            </button>
            <button
              role="tab"
              aria-selected={activePanel === "yonetim"}
              className={`rw-tab ${activePanel === "yonetim" ? "is-active" : ""}`}
              onClick={() => setActivePanel("yonetim")}
            >
              {t("Yönetim")}
            </button>
          </div>
          <div className="rw-inspector-body">
            <div className={`rw-tabpage ${activePanel === "test" ? "is-active" : ""}`}>
              <ScenarioPanel
                scenario={scenario}
                scenarioProvenance={scenarioProvenance}
                onSelectReference={handleSelectReference}
                onGenerateAI={handleGenerateAI}
                onRunBaseline={handleRunBaseline}
                isRunning={isRunningBaseline}
                isGenerating={isGenerating}
                generationError={generationError}
              />
              {appliedRobotLabel && (
                <p className="rw-hint" role="status">
                  {t("Uygulanan robot:")} <strong>{appliedRobotLabel}</strong> —{" "}
                  {t("gövde yarıçapı ve sensör değerleri bu robotunkilerle değiştirildi.")}
                </p>
              )}
              <ScenarioLibrary
                entries={library}
                activeScenarioId={scenario?.id ?? null}
                onSelect={handleSelectLibrary}
                disabled={busy}
              />
              <RobotPanel scenario={scenario} onScenarioChange={handleRobotApplied} />
              <LocalPolicyPanel
                info={localPolicyInfo}
                selected={selectedLocalPolicy}
                onSelect={setSelectedLocalPolicy}
              />
              <MapImport
                disabled={busy}
                onScenario={(s) => {
                  setScenario(s);
                  setScenarioProvenance("MAP_IMPORT");
                  setAppliedRobotLabel(null);
                  resetRunState(false);
                  setActivePanel("test");
                }}
              />
            </div>
            <div className={`rw-tabpage ${activePanel === "hata" ? "is-active" : ""}`}>
              <FailureAnalysis
                runId={activeRunId}
                runResult={runResult}
                minClearanceLimitM={scenario?.oracle.min_clearance_m}
                investigation={investigation}
                onInvestigate={handleInvestigate}
                onApplyPatch={handleApplyPatch}
              />
            </div>
            <div className={`rw-tabpage ${activePanel === "duzeltme" ? "is-active" : ""}`}>
              <PolicyProfiles candidatePolicy={candidatePolicy} onSelectProfile={setCandidatePolicy} />
              <FixComparison
                baselinePolicy={baselinePolicy}
                candidatePolicy={candidatePolicy}
                onUpdateCandidate={setCandidatePolicy}
                onVerify={handleVerify}
                isVerifying={isVerifying}
                hasBaseline={runFailed}
                provenance={provenance}
              />
            </div>
            <div className={`rw-tabpage ${activePanel === "sonuc" ? "is-active" : ""}`}>
              <VerificationDecision verification={verification} isVerifying={isVerifying} />
              <EvidencePanel verification={verification} />
              <VerificationHistory
                history={history.map((h) => ({
                  verification_id: h.verification_id,
                  verdict: h.verdict,
                  baseline_run_id: h.baseline_run_id,
                  created_at: h.created_at,
                }))}
                activeId={verification?.verification_id ?? null}
                onSelect={handleSelectHistory}
                onClear={() => {
                  setVerification(null);
                  try {
                    localStorage.removeItem("rw_verification_id");
                  } catch {
                    console.warn("localStorage unavailable");
                  }
                }}
              />
            </div>
            <div className={`rw-tabpage ${activePanel === "karne" ? "is-active" : ""}`}>
              <BatteryPanel onLoadRun={handleLoadBatteryRun} />
            </div>
            <div className={`rw-tabpage ${activePanel === "yonetim" ? "is-active" : ""}`}>
              <AdminPanel />
            </div>
          </div>
        </aside>
      </main>

      {/* Durum çubuğu */}
      <footer className="rw-statusbar">
        <span className="rw-status-cell">
          <span className={`dot ${backendUp ? "is-on" : "is-off"}`} />
          {backendUp ? t("Program bağlantısı: Çalışıyor") : t("Bağlantı yok — arka uç programı açık değil")}
        </span>
        <span className="rw-status-cell">
          Meta AI:{" "}
          {provenance === "LIVE_META"
            ? `${t("Canlı")}${metaModel ? ` (${metaModel})` : ""}`
            : t("Çevrimdışı yedek")}
        </span>
        <span className="rw-status-cell">{t("Adım:")} {currentStep + 1} / 4 — {t(STEPS[currentStep].name)}</span>
        <span className="rw-status-cell">
          {busy ? t("Çalışıyor…") : frames.length > 0 ? `${t("İzleniyor:")} ${currentFrameIndex + 1}. ${t("adım")}` : t("Hazır")}
        </span>
        <span className="rw-status-cell rw-status-right">RoboWitness</span>
      </footer>

      {/* Yardım penceresi */}
      {helpOpen && (
        <div className="rw-modal-backdrop" onClick={() => setHelpOpen(false)}>
          <div className="rw-modal" role="dialog" aria-modal="true" aria-label={t("Nasıl kullanılır?")} onClick={(e) => e.stopPropagation()}>
            <div className="rw-modal-head">
              <span className="rw-modal-title">{t("Nasıl Kullanılır?")}</span>
              <button className="rw-btn rw-btn-icon" onClick={() => setHelpOpen(false)} aria-label={t("Kapat")}>
                <X size={15} />
              </button>
            </div>
            <div className="rw-modal-body">
              <p>{t("Bu program, bir robotun hedefe çarpmadan gidip gidemediğini bilgisayarda test eder. Gerçek robota dokunmadan, güvenli bir şekilde deneme yaparsınız.")}</p>
              <div>
                <h4>{t("Yapmanız gerekenler (sırayla)")}</h4>
                <ol>
                  <li><strong>{t("Testi çalıştırın:")}</strong> {t("“Robotu Çalıştır”a basın. Robot eski ayarlarla hareket eder; ortadaki alanda tekrarını izleyin.")}</li>
                  <li><strong>{t("Hatayı inceleyin:")}</strong> {t("Robot çarparsa ya da hedefe ulaşamazsa “Hatayı İncele”ye basın. Meta AI ölçümlere bakıp nedeni açıklar ve yeni ayarlar önerir. (Bağlı değilse çevrimdışı yedek aynı işi yapar.)")}</li>
                  <li><strong>{t("Düzeltmeyi deneyin:")}</strong> {t("Öneriyi kullanın ya da kaydırıcılarla ayarları kendiniz değiştirin. “Düzeltmeyi Test Et”e basın.")}</li>
                  <li><strong>{t("Sonucu görün:")}</strong> {t("Program yeni ayarları aynı testte + görmediği 20 yeni testte dener. Karar:")} <strong>{t("KABUL EDİLDİ")}</strong> {t("ya da")} <strong>{t("REDDEDİLDİ")}</strong>. {t("Raporu indirip saklayabilirsiniz.")}</li>
                </ol>
              </div>
              <div>
                <h4>{t("Kelimeler ne demek?")}</h4>
                <dl>
                  <div><dt>{t("Eski ayarlar")}</dt><dd>{t("Robotun ilk çalıştırıldığı ayarlar.")}</dd></div>
                  <div><dt>{t("Yeni ayarlar")}</dt><dd>{t("Denemek istediğiniz düzeltme.")}</dd></div>
                  <div><dt>{t("Kontrol (1–5)")}</dt><dd>{t("Karar vermeden önce yapılan zorunlu sınavlar. Biri bile kalırsa düzeltme reddedilir.")}</dd></div>
                  <div><dt>{t("Mühürlü rapor")}</dt><dd>{t("Sonuç dosyası. Sonradan değiştirilirse anlaşılır; kanıt olarak saklanır.")}</dd></div>
                </dl>
              </div>
              <button className="rw-btn rw-btn-primary rw-btn-block" onClick={() => setHelpOpen(false)}>
                {t("Anladım, Başlayalım")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
