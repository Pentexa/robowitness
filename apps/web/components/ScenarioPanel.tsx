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
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">Test Seçimi</h3>
          <p className="rw-card-sub">Robot bu alanda, engellere çarpmadan hedefe gitmeye çalışacak.</p>
        </div>
      </div>
      <div className="rw-card-body">
        {scenario ? (
          <div className="rw-spec">
            <div className="rw-spec-item">
              <span className="rw-spec-label">Test alanı</span>
              <span className="rw-spec-value mono">
                {scenario.world.width_m} m × {scenario.world.height_m} m
              </span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Engel sayısı</span>
              <span className="rw-spec-value mono">
                {scenario.obstacles.length} adet ({scenario.kind === "dynamic_obstacle" ? "hareketli" : "sabit"})
              </span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Sensör gecikmesi</span>
              <span className="rw-spec-value mono">{scenario.robot.sensor_latency_ms} ms</span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Süre sınırı</span>
              <span className="rw-spec-value mono">{scenario.world.duration_limit_s} sn</span>
            </div>
          </div>
        ) : (
          <p className="rw-empty">Test yükleniyor… Program açık değilse soldaki durum çubuğunda “Bağlantı yok” yazar.</p>
        )}
        <p className="rw-hint">
          Sensör gecikmesi: robot etrafını biraz geç görür. Gecikme büyüdükçe çarpmak kolaylaşır.
        </p>
        {generationError && <p className="rw-err">Yeni test oluşturulamadı: {generationError}</p>}
        <div className="rw-actions">
          <button id="btn-run-baseline" className="rw-btn rw-btn-primary rw-btn-big" onClick={onRunBaseline} disabled={isRunning || isGenerating || !scenario}>
            <Play size={16} />
            {isRunning ? "Robot çalışıyor, bekleyin…" : "Robotu Çalıştır"}
          </button>
          <button id="btn-select-ref" className="rw-btn rw-btn-ghost" onClick={onSelectReference} disabled={isRunning || isGenerating}>
            <FolderOpen size={15} /> Hazır Testi Tekrar Yükle
          </button>
          <button id="btn-generate-ai" className="rw-btn rw-btn-ghost" onClick={onGenerateAI} disabled={isRunning || isGenerating || !scenario} title="Yapay zekâ ile yeni bir test oluşturur">
            <Sparkles size={15} />
            {isGenerating ? "Oluşturuluyor…" : "Yapay Zekâyla Yeni Test Oluştur"}
          </button>
        </div>
        <details className="rw-details">
          <summary>Teknik detaylar (isteğe bağlı)</summary>
          <div>
            <span className="mono text-xs">Test kodu: {scenario ? scenario.id : "—"}</span>
            <span className="mono text-xs">Rastgelelik tohumu (seed): {scenario ? scenario.seed : "—"}</span>
            <span className="mono text-xs">Kaynak: {scenarioProvenance}</span>
          </div>
        </details>
      </div>
    </div>
  );
};
