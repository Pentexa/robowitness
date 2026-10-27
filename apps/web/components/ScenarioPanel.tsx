"use client";

import React from "react";
import { ScenarioSpec } from "../lib/types";

interface ScenarioPanelProps {
  scenario: ScenarioSpec | null;
  onSelectReference: () => void;
  onRunBaseline: () => void;
  isRunning: boolean;
}

export const ScenarioPanel: React.FC<ScenarioPanelProps> = ({
  scenario,
  onSelectReference,
  onRunBaseline,
  isRunning,
}) => {
  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">1. Scenario Definition</h3>
        <span className="badge badge-primary">RW-REF-001</span>
      </div>

      <div className="card-body">
        {scenario ? (
          <div className="spec-grid">
            <div className="spec-item">
              <span className="spec-label">Environment</span>
              <span className="spec-value">
                {scenario.world.width_m}m x {scenario.world.height_m}m Warehouse
              </span>
            </div>
            <div className="spec-item">
              <span className="spec-label">Seed</span>
              <span className="spec-value">{scenario.seed}</span>
            </div>
            <div className="spec-item">
              <span className="spec-label">Sensor Latency</span>
              <span className="spec-value font-mono text-warning">
                {scenario.robot.sensor_latency_ms} ms
              </span>
            </div>
            <div className="spec-item">
              <span className="spec-label">Obstacles</span>
              <span className="spec-value">{scenario.obstacles.length} Dynamic</span>
            </div>
          </div>
        ) : (
          <p className="text-muted">Loading scenario specification...</p>
        )}

        <div className="action-row mt-4">
          <button
            id="btn-select-ref"
            className="btn btn-secondary"
            onClick={onSelectReference}
            disabled={isRunning}
          >
            Reload Reference
          </button>
          <button
            id="btn-run-baseline"
            className="btn btn-danger"
            onClick={onRunBaseline}
            disabled={isRunning || !scenario}
          >
            {isRunning ? "Simulating..." : "Execute Baseline Run"}
          </button>
        </div>
      </div>
    </div>
  );
};
