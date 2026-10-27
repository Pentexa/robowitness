"use client";

import React, { useEffect, useState } from "react";
import { EvidencePanel } from "../components/EvidencePanel";
import { FixComparison } from "../components/FixComparison";
import { ReplayControls } from "../components/ReplayControls";
import { ScenarioPanel } from "../components/ScenarioPanel";
import { SimulationCanvas } from "../components/SimulationCanvas";
import { Timeline } from "../components/Timeline";
import { VerificationDecision } from "../components/VerificationDecision";
import {
  createRun,
  fetchHealth,
  fetchJob,
  fetchReferenceScenarios,
  fetchRun,
  fetchTelemetry,
  investigateFailure,
  verifyFix,
  fetchVerification,
} from "../lib/api";
import {
  PolicyConfig,
  ScenarioSpec,
  TelemetryFrame,
  VerificationRecord,
} from "../lib/types";

const DEFAULT_BASELINE_POLICY: PolicyConfig = {
  schema_version: "1.0",
  id: "baseline-v1",
  max_speed_mps: 0.75,
  safe_distance_m: 0.30,
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
  obstacle_prediction_horizon_s: 0.60,
};

export default function DashboardPage() {
  const [scenario, setScenario] = useState<ScenarioSpec | null>(null);
  const [baselinePolicy] = useState<PolicyConfig>(DEFAULT_BASELINE_POLICY);
  const [candidatePolicy, setCandidatePolicy] = useState<PolicyConfig>(DEFAULT_CANDIDATE_POLICY);

  const [frames, setFrames] = useState<TelemetryFrame[]>([]);
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(1.0);

  const [isRunningBaseline, setIsRunningBaseline] = useState<boolean>(false);
  const [isVerifying, setIsVerifying] = useState<boolean>(false);

  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [verification, setVerification] = useState<VerificationRecord | null>(null);
  const [provenance, setProvenance] = useState<string>("OFFLINE_REFERENCE");
  const [backendStatus, setBackendStatus] = useState<string>("connecting");

  // Load health and default reference scenario on mount
  useEffect(() => {
    fetchHealth()
      .then((h) => {
        setBackendStatus(h.status === "healthy" ? "online" : "degraded");
        setProvenance(h.ai_mode === "live" ? "LIVE_META" : "OFFLINE_REFERENCE");
      })
      .catch(() => setBackendStatus("offline"));

    fetchReferenceScenarios()
      .then((scenarios) => {
        if (scenarios.length > 0) setScenario(scenarios[0]);
      })
      .catch((err) => console.error("Could not load scenarios:", err));
  }, []);

  // Animation frame replay loop
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isPlaying && frames.length > 0) {
      const intervalMs = (1000 / 60) / speed;
      timer = setInterval(() => {
        setCurrentFrameIndex((prev) => {
          if (prev >= frames.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, intervalMs);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, frames, speed]);

  const handleRunBaseline = async () => {
    if (!scenario) return;
    setIsRunningBaseline(true);
    setIsPlaying(false);
    setCurrentFrameIndex(0);

    try {
      const runJob = await createRun(scenario, baselinePolicy);
      const pollInterval = setInterval(async () => {
        const job = await fetchJob(runJob.job_id);
        if (job.status === "completed") {
          clearInterval(pollInterval);
          setIsRunningBaseline(false);
          setActiveRunId(runJob.result_id);

          const telemetryData = await fetchTelemetry(runJob.result_id);
          setFrames(telemetryData.frames);
          setIsPlaying(true);
        } else if (job.status === "failed") {
          clearInterval(pollInterval);
          setIsRunningBaseline(false);
          alert(`Simulation run failed: ${job.error_code}`);
        }
      }, 750);
    } catch (e) {
      setIsRunningBaseline(false);
      console.error(e);
    }
  };

  const handleVerify = async () => {
    if (!activeRunId) {
      alert("Please execute a baseline run before submitting verification.");
      return;
    }
    setIsVerifying(true);

    try {
      const verifJob = await verifyFix(activeRunId, candidatePolicy);
      const pollInterval = setInterval(async () => {
        const job = await fetchJob(verifJob.job_id);
        if (job.status === "completed") {
          clearInterval(pollInterval);
          setIsVerifying(false);
          const record = await fetchVerification(verifJob.result_id);
          setVerification(record);
        } else if (job.status === "failed") {
          clearInterval(pollInterval);
          setIsVerifying(false);
          alert(`Verification failed: ${job.error_code}`);
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
      <header className="app-header">
        <div className="header-brand">
          <div className="brand-icon">RW</div>
          <div>
            <h1 className="brand-title">RoboWitness</h1>
            <p className="text-xs text-muted">Independent Verification Engine for Robotics Policy Fixes</p>
          </div>
        </div>

        <div className="header-status">
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">Backend:</span>
            <span className={`badge ${backendStatus === "online" ? "badge-success" : "badge-danger"}`}>
              {backendStatus.toUpperCase()}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted">AI Provenance:</span>
            <span className="badge badge-info">{provenance}</span>
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* Left Column: Canvas Replay & Controls */}
        <section className="flex flex-col gap-4">
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">Authoritative 2D Simulation View</h2>
              <span className="badge badge-primary font-mono text-xs">
                {frames.length > 0 ? `${frames.length} FRAMES` : "READY"}
              </span>
            </div>

            <div className="card-body">
              <SimulationCanvas
                scenario={scenario}
                frames={frames}
                currentFrameIndex={currentFrameIndex}
              />

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
        </section>

        {/* Right Column: Scenario, Fix Comparison, Gate Protocol */}
        <section className="flex flex-col gap-4">
          <ScenarioPanel
            scenario={scenario}
            onSelectReference={() => {
              fetchReferenceScenarios().then((s) => s.length && setScenario(s[0]));
            }}
            onRunBaseline={handleRunBaseline}
            isRunning={isRunningBaseline}
          />

          <FixComparison
            baselinePolicy={baselinePolicy}
            candidatePolicy={candidatePolicy}
            onUpdateCandidate={setCandidatePolicy}
            onVerify={handleVerify}
            isVerifying={isVerifying}
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
