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
    <div className="rw-card">
      <div className="rw-card-head">
        <h3 className="rw-card-title">1. Scenario Definition</h3>
        <span className="rw-badge mono">{scenario ? scenario.id : "—"}</span>
      </div>

      <div className="rw-card-body">
        {scenario ? (
          <div className="rw-spec">
            <div className="rw-spec-item">
              <span className="rw-spec-label">Environment</span>
              <span className="rw-spec-value">
                {scenario.world.width_m}m × {scenario.world.height_m}m
              </span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Seed</span>
              <span className="rw-spec-value mono">{scenario.seed}</span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Sensor latency</span>
              <span className="rw-spec-value mono">{scenario.robot.sensor_latency_ms} ms</span>
            </div>
            <div className="rw-spec-item">
              <span className="rw-spec-label">Obstacles</span>
              <span className="rw-spec-value">
                {scenario.obstacles.length} {scenario.kind === "dynamic_obstacle" ? "dynamic" : "static"}
              </span>
            </div>
          </div>
        ) : (
          <p className="rw-empty">Loading scenario specification…</p>
        )}

        <div className="rw-actions">
          <button
            id="btn-select-ref"
            className="rw-btn rw-btn-ghost"
            onClick={onSelectReference}
            disabled={isRunning}
          >
            Reload reference
          </button>
          <button
            id="btn-run-baseline"
            className="rw-btn rw-btn-primary"
            onClick={onRunBaseline}
            disabled={isRunning || !scenario}
          >
            {isRunning ? "Simulating…" : "Execute baseline run"}
          </button>
        </div>
      </div>
    </div>
  );
};
