"use client";

import React from "react";
import { Play, Pause, RotateCcw, SkipBack, SkipForward } from "lucide-react";

interface ReplayControlsProps {
  isPlaying: boolean;
  onTogglePlay: () => void;
  onReset: () => void;
  onStepForward: () => void;
  onStepBackward: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  currentSimTime: number;
  totalDuration: number;
}

export const ReplayControls: React.FC<ReplayControlsProps> = ({
  isPlaying,
  onTogglePlay,
  onReset,
  onStepForward,
  onStepBackward,
  speed,
  onSpeedChange,
  currentSimTime,
  totalDuration,
}) => {
  return (
    <div className="replay-controls">
      <div className="btn-group">
        <button id="btn-replay-reset" className="btn btn-icon" onClick={onReset} title="Reset to Start">
          <RotateCcw size={16} />
        </button>
        <button id="btn-replay-prev" className="btn btn-icon" onClick={onStepBackward} title="Previous Tick">
          <SkipBack size={16} />
        </button>
        <button id="btn-replay-play" className="btn btn-primary btn-icon" onClick={onTogglePlay}>
          {isPlaying ? <Pause size={18} /> : <Play size={18} />}
        </button>
        <button id="btn-replay-next" className="btn btn-icon" onClick={onStepForward} title="Next Tick">
          <SkipForward size={16} />
        </button>
      </div>

      <div className="time-display font-mono">
        <span className="text-white">{currentSimTime.toFixed(2)}s</span>
        <span className="text-muted"> / {totalDuration.toFixed(2)}s</span>
      </div>

      <div className="speed-toggles">
        {[0.5, 1.0, 2.0].map((s) => (
          <button
            key={s}
            className={`btn btn-sm ${speed === s ? "btn-active" : "btn-secondary"}`}
            onClick={() => onSpeedChange(s)}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
};
