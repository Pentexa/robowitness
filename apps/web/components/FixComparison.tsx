"use client";

import React, { useState } from "react";
import { PolicyConfig } from "../lib/types";

interface FixComparisonProps {
  baselinePolicy: PolicyConfig;
  candidatePolicy: PolicyConfig;
  onUpdateCandidate: (updated: PolicyConfig) => void;
  onVerify: () => void;
  isVerifying: boolean;
  provenance: string;
}

export const FixComparison: React.FC<FixComparisonProps> = ({
  baselinePolicy,
  candidatePolicy,
  onUpdateCandidate,
  onVerify,
  isVerifying,
  provenance,
}) => {
  const handleChange = (field: keyof PolicyConfig, value: number) => {
    onUpdateCandidate({
      ...candidatePolicy,
      [field]: value,
    });
  };

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">2. Policy Fix Comparison</h3>
        <span className="badge badge-info font-mono">{provenance}</span>
      </div>

      <div className="card-body">
        <div className="param-comparison-table">
          <div className="table-header">
            <span>Parameter</span>
            <span>Baseline</span>
            <span>Candidate (AI Proposal)</span>
          </div>

          <div className="table-row">
            <span className="param-name">Max Speed (m/s)</span>
            <span className="font-mono text-muted">{baselinePolicy.max_speed_mps}</span>
            <input
              id="input-max-speed"
              type="number"
              step="0.05"
              min="0.05"
              max="1.20"
              value={candidatePolicy.max_speed_mps}
              onChange={(e) => handleChange("max_speed_mps", parseFloat(e.target.value))}
              className="input-sm font-mono"
            />
          </div>

          <div className="table-row">
            <span className="param-name">Safe Distance (m)</span>
            <span className="font-mono text-muted">{baselinePolicy.safe_distance_m}</span>
            <input
              id="input-safe-distance"
              type="number"
              step="0.05"
              min="0.20"
              max="2.00"
              value={candidatePolicy.safe_distance_m}
              onChange={(e) => handleChange("safe_distance_m", parseFloat(e.target.value))}
              className="input-sm font-mono"
            />
          </div>

          <div className="table-row">
            <span className="param-name">Reaction Margin (m)</span>
            <span className="font-mono text-muted">{baselinePolicy.reaction_margin_m}</span>
            <input
              id="input-reaction-margin"
              type="number"
              step="0.05"
              min="0.00"
              max="1.00"
              value={candidatePolicy.reaction_margin_m}
              onChange={(e) => handleChange("reaction_margin_m", parseFloat(e.target.value))}
              className="input-sm font-mono"
            />
          </div>

          <div className="table-row">
            <span className="param-name">Brake Gain</span>
            <span className="font-mono text-muted">{baselinePolicy.brake_gain}</span>
            <input
              id="input-brake-gain"
              type="number"
              step="0.1"
              min="0.1"
              max="10.0"
              value={candidatePolicy.brake_gain}
              onChange={(e) => handleChange("brake_gain", parseFloat(e.target.value))}
              className="input-sm font-mono"
            />
          </div>

          <div className="table-row">
            <span className="param-name">Prediction Horizon (s)</span>
            <span className="font-mono text-muted">{baselinePolicy.obstacle_prediction_horizon_s}</span>
            <input
              id="input-prediction-horizon"
              type="number"
              step="0.1"
              min="0.0"
              max="2.0"
              value={candidatePolicy.obstacle_prediction_horizon_s}
              onChange={(e) => handleChange("obstacle_prediction_horizon_s", parseFloat(e.target.value))}
              className="input-sm font-mono"
            />
          </div>
        </div>

        <div className="mt-4">
          <button
            id="btn-verify-fix"
            className="btn btn-primary w-full"
            onClick={onVerify}
            disabled={isVerifying}
          >
            {isVerifying ? "Executing Verification Sequence..." : "Run Independent Verification Protocol"}
          </button>
        </div>
      </div>
    </div>
  );
};
