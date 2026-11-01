"use client";

import React from "react";
import { Library } from "lucide-react";
import { ScenarioCatalogEntry } from "../lib/types";

interface ScenarioLibraryProps {
  entries: ScenarioCatalogEntry[];
  activeScenarioId: string | null;
  onSelect: (entry: ScenarioCatalogEntry) => void;
  disabled: boolean;
}

export const ScenarioLibrary: React.FC<ScenarioLibraryProps> = ({
  entries,
  activeScenarioId,
  onSelect,
  disabled,
}) => {
  const active = entries.find((e) => e.scenario.id === activeScenarioId) ?? null;
  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">Test Senaryosu Kütüphanesi</h3>
          <p className="rw-card-sub">
            {entries.length > 0
              ? `${entries.length} hazır senaryo: dar koridor, slalom, karşıdan gelen engel, yüksek gecikme ve daha fazlası.`
              : "Kütüphane yükleniyor…"}
          </p>
        </div>
      </div>
      <div className="rw-card-body">
        <label className="rw-field">
          <span>Senaryo seçin</span>
          <select
            id="select-library-scenario"
            className="rw-input"
            value={active?.scenario.id ?? ""}
            disabled={disabled || entries.length === 0}
            onChange={(e) => {
              const entry = entries.find((x) => x.scenario.id === e.target.value);
              if (entry) onSelect(entry);
            }}
          >
            <option value="">— Kütüphaneden seçin —</option>
            {entries.map((e) => (
              <option key={e.scenario.id} value={e.scenario.id}>
                {e.title} ({e.difficulty}) — {e.category}
              </option>
            ))}
          </select>
        </label>
        {active && (
          <div className="rw-spec">
            <div className="rw-spec-item">
              <span className="rw-spec-label">Açıklama</span>
              <span className="rw-spec-value">{active.description}</span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Zorluk / Tür</span>
              <span className="rw-spec-value">
                {active.difficulty} · {active.category}
                {active.tags.length > 0 ? ` · ${active.tags.join(", ")}` : ""}
              </span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Engel / Gecikme</span>
              <span className="rw-spec-value mono">
                {active.scenario.obstacles.length} engel · {active.scenario.robot.sensor_latency_ms} ms · gürültü{" "}
                {active.scenario.robot.sensor_noise_std_m} m
              </span>
            </div>
          </div>
        )}
        <p className="rw-hint">
          <Library size={13} /> Senaryo seçmek, üstteki test alanını o senaryoyla değiştirir. Sonra “Robotu
          Çalıştır” ile deneyebilirsiniz. Eski hazır test (referans) için “Hazır Testi Tekrar Yükle”yi kullanın.
        </p>
      </div>
    </div>
  );
};
