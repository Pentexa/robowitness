"use client";

import React from "react";
import { FolderOpen, Play, Sparkles } from "lucide-react";
import { ScenarioSpec } from "../lib/types";

interface ScenarioPanelProps {
  scenario: ScenarioSpec | null;
  scenarioProvenance: string;
  onSelectReference: () => void;
  onGenerateAI: () => void;
  onRunBaseline: () => void;
  isRunning: boolean;
  isGenerating: boolean;
  generationError: string | null;
}

export const ScenarioPanel: React.FC<ScenarioPanelProps> = ({
  scenario,
  scenarioProvenance,
  onSelectReference,
  onGenerateAI,
  onRunBaseline,
  isRunning,
  isGenerating,
  generationError,
}) => {
  return (
    <section className="rw-section">
      <h3 className="rw-section-title">Senaryo</h3>
      {scenario ? (
        <p className="rw-summary mono">
          {scenario.id} · {scenario.world.width_m}×{scenario.world.height_m} m ·{" "}
          {scenario.obstacles.length} engel · gecikme {scenario.robot.sensor_latency_ms} ms ·{" "}
          {scenario.world.duration_limit_s} sn
        </p>
      ) : (
        <p className="rw-summary">Test yükleniyor…</p>
      )}
      {generationError && <p className="rw-err">Yeni test oluşturulamadı: {generationError}</p>}
      <button
        id="btn-run-baseline"
        className="rw-btn rw-btn-primary rw-btn-big"
        onClick={onRunBaseline}
        disabled={isRunning || isGenerating || !scenario}
      >
        <Play size={16} />
        {isRunning ? "Robot çalışıyor…" : "Robotu Çalıştır"}
      </button>
      <div className="rw-btn-row">
        <button id="btn-select-ref" className="rw-btn rw-btn-ghost rw-btn-sm" onClick={onSelectReference} disabled={isRunning || isGenerating}>
          <FolderOpen size={14} /> Hazır Test
        </button>
        <button
          id="btn-generate-ai"
          className="rw-btn rw-btn-ghost rw-btn-sm"
          onClick={onGenerateAI}
          disabled={isRunning || isGenerating || !scenario}
          title="Meta AI ile yeni bir test senaryosu oluşturur"
        >
          <Sparkles size={14} />
          {isGenerating ? "Meta AI üretiyor…" : "Meta AI ile Üret"}
        </button>
      </div>
      <details className="rw-details">
        <summary>Teknik detaylar</summary>
        <div>
          <span className="mono text-xs">Seed: {scenario ? scenario.seed : "—"} · Kaynak: {scenarioProvenance}</span>
        </div>
      </details>
    </section>
  );
};
