"use client";

import React from "react";
import { TelemetryFrame } from "../lib/types";

interface TimelineProps {
  frames: TelemetryFrame[];
  currentIndex: number;
  onSeek: (index: number) => void;
}

export const Timeline: React.FC<TimelineProps> = ({ frames, currentIndex, onSeek }) => {
  const total = frames.length;
  if (total <= 1) return null;

  const collisionFrames = frames
    .map((f, i) => (f.events.some((e) => e.type === "COLLISION") ? i : -1))
    .filter((i) => i >= 0);

  return (
    <div className="timeline-container">
      <div className="timeline-track-wrapper">
        <input
          id="timeline-scrubber"
          type="range"
          min={0}
          max={total - 1}
          value={currentIndex}
          onChange={(e) => onSeek(parseInt(e.target.value, 10))}
          className="timeline-range"
        />

        {/* Collision event markers on timeline track */}
        <div className="timeline-markers">
          {collisionFrames.map((idx) => {
            const leftPct = (idx / (total - 1)) * 100;
            return (
              <span
                key={idx}
                className="timeline-marker-collision"
                style={{ left: `${leftPct}%` }}
                title={`Collision at Tick ${idx}`}
              />
            );
          })}
        </div>
      </div>

      <div className="timeline-footer font-mono text-xs text-muted">
        <span>Tick: {frames[currentIndex]?.tick ?? 0}</span>
        <span>Clearance: {frames[currentIndex]?.clearance_m.toFixed(3) ?? 0}m</span>
        <span>Speed: {frames[currentIndex]?.command.linear_mps.toFixed(2) ?? 0}m/s</span>
      </div>
    </div>
  );
};
