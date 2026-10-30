"use client";

import React from "react";
import { PolicyConfig } from "../lib/types";

interface FixComparisonProps {
  baselinePolicy: PolicyConfig;
  candidatePolicy: PolicyConfig;
  onUpdateCandidate: (updated: PolicyConfig) => void;
  onVerify: () => void;
  isVerifying: boolean;
  hasBaseline: boolean;
  provenance: string;
}

const FIELDS: Array<{
  key: "max_speed_mps" | "safe_distance_m" | "reaction_margin_m" | "brake_gain" | "obstacle_prediction_horizon_s";
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
}> = [
  { key: "max_speed_mps", label: "Max speed", unit: "m/s", min: 0.05, max: 1.2, step: 0.05 },
  { key: "safe_distance_m", label: "Safe distance", unit: "m", min: 0.2, max: 2.0, step: 0.05 },
  { key: "reaction_margin_m", label: "Reaction margin", unit: "m", min: 0.0, max: 1.0, step: 0.05 },
  { key: "brake_gain", label: "Brake gain", unit: "×", min: 0.1, max: 10.0, step: 0.1 },
  { key: "obstacle_prediction_horizon_s", label: "Prediction horizon", unit: "s", min: 0.0, max: 2.0, step: 0.1 },
];

export const FixComparison: React.FC<FixComparisonProps> = ({
  baselinePolicy,
  candidatePolicy,
  onUpdateCandidate,
  onVerify,
  isVerifying,
  hasBaseline,
  provenance,
}) => {
  const handleChange = (field: keyof PolicyConfig, value: number) => {
    if (!Number.isFinite(value)) return;
    onUpdateCandidate({ ...candidatePolicy, [field]: value });
  };

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <h3 className="rw-card-title">3. Policy Fix Comparison</h3>
        <span className="rw-badge mono">
          <span className="dot" />
          {provenance}
        </span>
      </div>

      <div className="rw-card-body">
        <div>
          <div className="rw-table-head">
            <span>Parameter</span>
            <span>Baseline</span>
            <span>Candidate</span>
          </div>
          {FIELDS.map((f) => {
            const base = baselinePolicy[f.key] as number;
            const cand = candidatePolicy[f.key] as number;
            const changed = base !== cand;
            return (
              <div className="rw-table-row" key={f.key}>
                <span>
                  {f.label} <span className="muted text-xs">({f.unit})</span>
                </span>
                <span className="mono muted">{base.toFixed(2)}</span>
                <input
                  id={`input-${f.key.replace(/_/g, "-")}`}
                  type="number"
                  step={f.step}
                  min={f.min}
                  max={f.max}
                  value={cand}
                  onChange={(e) => handleChange(f.key, parseFloat(e.target.value))}
                  className="rw-input"
                  style={changed ? { borderColor: "var(--accent-line)" } : undefined}
                  aria-label={`Candidate ${f.label}`}
                />
              </div>
            );
          })}
        </div>

        <button
          id="btn-verify-fix"
          className="rw-btn rw-btn-primary rw-btn-block"
          onClick={onVerify}
          disabled={isVerifying || !hasBaseline}
          title={hasBaseline ? undefined : "Run a baseline first"}
        >
          {isVerifying ? "Executing verification sequence…" : "Run independent verification protocol"}
        </button>
      </div>
    </div>
  );
};
