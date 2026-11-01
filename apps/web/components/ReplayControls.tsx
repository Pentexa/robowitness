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
    <div className="rw-player">
      <div className="rw-btn-group">
        <button id="btn-replay-reset" className="rw-btn rw-btn-icon" onClick={onReset} title="En başa dön" aria-label="En başa dön">
          <RotateCcw size={15} />
        </button>
        <button id="btn-replay-prev" className="rw-btn rw-btn-icon" onClick={onStepBackward} title="Bir adım geri" aria-label="Bir adım geri">
          <SkipBack size={15} />
        </button>
        <button id="btn-replay-play" className={`rw-btn rw-btn-icon ${isPlaying ? "is-on" : ""}`} onClick={onTogglePlay} title={isPlaying ? "Duraklat" : "Oynat"} aria-label={isPlaying ? "Duraklat" : "Oynat"}>
          {isPlaying ? <Pause size={15} /> : <Play size={15} />}
        </button>
        <button id="btn-replay-next" className="rw-btn rw-btn-icon" onClick={onStepForward} title="Bir adım ileri" aria-label="Bir adım ileri">
          <SkipForward size={15} />
        </button>
      </div>
      <div className="rw-time">
        <span>{currentSimTime.toFixed(2)} sn</span>
        <span className="dim"> / {totalDuration.toFixed(2)} sn</span>
      </div>
      <div className="rw-btn-group" aria-label="Oynatma hızı">
        {[0.5, 1.0, 2.0].map((s) => (
          <button
            key={s}
            className={`rw-btn rw-btn-sm mono ${speed === s ? "rw-btn-primary" : "rw-btn-ghost"}`}
            onClick={() => onSpeedChange(s)}
            title={`${s} kat hızla oynat`}
          >
            {s}×
          </button>
        ))}
      </div>
    </div>
  );
};
