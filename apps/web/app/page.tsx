"use client";

import React, { useEffect, useState } from "react";
import { ComparisonReplay } from "../components/ComparisonReplay";
import { EvidencePanel } from "../components/EvidencePanel";
import { FailureAnalysis } from "../components/FailureAnalysis";
import { FixComparison } from "../components/FixComparison";
import { ReplayControls } from "../components/ReplayControls";
import { ScenarioPanel } from "../components/ScenarioPanel";
import { SimulationCanvas } from "../components/SimulationCanvas";
import { SimulationCanvas3D } from "../components/SimulationCanvas3D";
import { Timeline } from "../components/Timeline";
import { VerificationDecision } from "../components/VerificationDecision";
import {
  createRun,
  fetchHealth,
  fetchJob,
  fetchReferenceScenarios,
  fetchTelemetry,
  fetchVerification,
  investigateFailure,
  verifyFix,
} from "../lib/api";
import {
  InvestigationResponse,
  PolicyConfig,
  PolicyPatch,
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

export default function DashboardPage() {
  const [scenario, setScenario] = useState<ScenarioSpec | null>(null);
  const [baselinePolicy] = useState<PolicyConfig>(DEFAULT_BASELINE_POLICY);
  const [candidatePolicy, setCandidatePolicy] = useState<PolicyConfig>(DEFAULT_CANDIDATE_POLICY);
  const [viewMode, setViewMode] = useState<"2d" | "3d">("2d");

  const [frames, setFrames] = useState<TelemetryFrame[]>([]);
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(1.0);

  const [isRunningBaseline, setIsRunningBaseline] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [investigation, setInvestigation] = useState<InvestigationResponse | null>(null);
  const [verification, setVerification] = useState<VerificationRecord | null>(null);
  const [provenance, setProvenance] = useState<string>("OFFLINE_REFERENCE");
  const [backendUp, setBackendUp] = useState<boolean>(false);

  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setBackendUp(h.status === "healthy");
        setProvenance(h.ai_mode === "live" ? "LIVE_META" : "OFFLINE_REFERENCE");
      })
      .catch(() => setBackendUp(false));

    fetchReferenceScenarios()
      .then((scenarios) => {
        if (scenarios.length > 0) setScenario(scenarios[0]);
      })
      .catch((err) => console.error("Could not load scenarios:", err));

    try {
      const savedRunId = localStorage.getItem("rw_run_id");
      const savedVerifId = localStorage.getItem("rw_verification_id");
      if (savedRunId) {
        setActiveRunId(savedRunId);
        fetchTelemetry(savedRunId)
          .then((d) => setFrames(d.frames))
          .catch(() => console.warn("Saved run telemetry unavailable"));
      }
      if (savedVerifId) {
        fetchVerification(savedVerifId)
          .then((record) => setVerification(record))
          .catch(() => console.warn("Saved verification record unavailable"));
      }
    } catch {
      console.warn("localStorage unavailable; refresh recovery disabled");
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

  const handleRunBaseline = async () => {
    if (!scenario) return;
    setIsRunningBaseline(true);
    setIsPlaying(false);
    setCurrentFrameIndex(0);
    setInvestigation(null);
    try {
      const runJob = await createRun(scenario, baselinePolicy);
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
            const telemetryData = await fetchTelemetry(runJob.result_id);
            setFrames(telemetryData.frames);
            setIsPlaying(true);
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
  };

  const handleVerify = async () => {
    if (!activeRunId) return;
    setIsVerifying(true);
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

  const currentSimTime = frames[currentFrameIndex]?.sim_time_s ?? 0.0;
  const totalDuration = frames[frames.length - 1]?.sim_time_s ?? 0.0;

  return (
    <div>
      <header className="rw-header">
        <div className="rw-header-inner">
          <div className="rw-brand">
            <div className="rw-mark">RW</div>
            <div>
              <h1 className="rw-title">RoboWitness</h1>
              <p className="rw-subtitle">Independent Verification Engine</p>
            </div>
          </div>
          <div className="rw-status">
            <span className={`rw-badge ${backendUp ? "is-live" : "is-fail"}`}>
              <span className="dot" />
              {backendUp ? "BACKEND ONLINE" : "BACKEND OFFLINE"}
            </span>
            <span className="rw-badge">
              <span className="dot" />
              {provenance}
            </span>
          </div>
        </div>
      </header>

      <main className="rw-main">
        <section className="rw-col">
          <div className="rw-card">
            <div className="rw-card-head">
              <h2 className="rw-card-title">Simulation Replay</h2>
              <div className="rw-row">
                <div className="rw-btn-group">
                  <button
                    id="btn-view-2d"
                    className={`rw-btn rw-btn-sm ${viewMode === "2d" ? "rw-btn-primary" : "rw-btn-ghost"}`}
                    onClick={() => setViewMode("2d")}
                  >
                    2D
                  </button>
                  <button
                    id="btn-view-3d"
                    className={`rw-btn rw-btn-sm ${viewMode === "3d" ? "rw-btn-primary" : "rw-btn-ghost"}`}
                    onClick={() => setViewMode("3d")}
                  >
                    3D
                  </button>
                </div>
                <span className="rw-badge mono">
                  {frames.length > 0 ? `${frames.length} FRAMES` : "READY"}
                </span>
              </div>
            </div>
            <div className="rw-card-body">
              {viewMode === "2d" ? (
                <SimulationCanvas
                  scenario={scenario}
                  frames={frames}
                  currentFrameIndex={currentFrameIndex}
                />
              ) : (
                <SimulationCanvas3D
                  scenario={scenario}
                  frames={frames}
                  currentFrameIndex={currentFrameIndex}
                />
              )}
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
        </section>

        <section className="rw-col">
          <ScenarioPanel
            scenario={scenario}
            onSelectReference={() => {
              fetchReferenceScenarios().then((s) => s.length && setScenario(s[0]));
            }}
            onRunBaseline={handleRunBaseline}
            isRunning={isRunningBaseline}
          />

          <FailureAnalysis
            runId={activeRunId}
            investigation={investigation}
            onInvestigate={handleInvestigate}
            onApplyPatch={handleApplyPatch}
          />

          <FixComparison
            baselinePolicy={baselinePolicy}
            candidatePolicy={candidatePolicy}
            onUpdateCandidate={setCandidatePolicy}
            onVerify={handleVerify}
            isVerifying={isVerifying}
            hasBaseline={activeRunId !== null}
            provenance={provenance}
          />

          <VerificationDecision
            verification={verification}
            isVerifying={isVerifying}
          />

          <EvidencePanel verification={verification} />
        </section>
      </main>
    </div>
  );
}
