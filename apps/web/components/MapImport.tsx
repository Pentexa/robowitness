"use client";

import React, { useState } from "react";
import { Map as MapIcon } from "lucide-react";
import { convertMapToScenario } from "../lib/api";
import { ScenarioSpec } from "../lib/types";

const SAMPLE_GRID = [
  "........................",
  ".S........##............",
  "..........##......G.....",
  "..........##............",
  "........................",
  "........................",
  "........................",
  "........................",
  "........................",
  "........................",
  "........................",
  "........................",
].join("\n");

interface MapImportProps {
  onScenario: (scenario: ScenarioSpec) => void;
  disabled: boolean;
}

export const MapImport: React.FC<MapImportProps> = ({ onScenario, disabled }) => {
  const [grid, setGrid] = useState<string>(SAMPLE_GRID);
  const [cellSize, setCellSize] = useState<string>("0.5");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  const handleConvert = async () => {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      const { scenario, warnings } = await convertMapToScenario(
        "Haritam",
        grid,
        parseFloat(cellSize) || 0.5
      );
      onScenario(scenario);
      setNotice(
        `Harita senaryoya çevrildi: ${scenario.id} (${scenario.obstacles.length} engel)` +
          (warnings.length ? ` — ${warnings.join(" ")}` : "")
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Harita çevrilemedi");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="rw-section">
      <h3 className="rw-section-title">Haritamdan Senaryo (Kendi Ortamım)</h3>
      <p className="rw-summary">
        Ortamınızı ızgara olarak çizin: <span className="mono">#</span> engel,{" "}
        <span className="mono">.</span> boş, <span className="mono">S</span> başlangıç,{" "}
        <span className="mono">G</span> hedef. Her engel kümesi tek bir dairesel engele çevrilir (en
        çok 8). Dünya boyutu 6–20 m × 4–15 m olmalı.
      </p>
      <textarea
        id="textarea-map-grid"
        className="rw-input mono"
        rows={8}
        value={grid}
        onChange={(e) => setGrid(e.target.value)}
        aria-label="Harita ızgarası"
        spellCheck={false}
      />
      <div className="rw-btn-row">
        <label className="rw-field" style={{ flex: 1 }}>
          <span>Hücre boyutu (m)</span>
          <input
            className="rw-input"
            type="number"
            step="0.1"
            value={cellSize}
            onChange={(e) => setCellSize(e.target.value)}
          />
        </label>
        <button
          id="btn-convert-map"
          className="rw-btn rw-btn-primary"
          onClick={handleConvert}
          disabled={disabled || busy}
          style={{ alignSelf: "flex-end" }}
        >
          <MapIcon size={15} /> Senaryoya Çevir ve Kullan
        </button>
      </div>
      {error && <p className="rw-err">{error}</p>}
      {notice && <p className="rw-summary" role="status">{notice}</p>}
    </section>
  );
};
