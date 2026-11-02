"use client";

import React from "react";
import { Play, Pause, RotateCcw, SkipBack, SkipForward } from "lucide-react";
import { useLocale } from "../lib/i18n";

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
  const { t } = useLocale();
  return (
    <div className="rw-player">
      <div className="rw-btn-group">
        <button id="btn-replay-reset" className="rw-btn rw-btn-icon" onClick={onReset} title={t("En başa dön")} aria-label={t("En başa dön")}>
          <RotateCcw size={15} />
        </button>
        <button id="btn-replay-prev" className="rw-btn rw-btn-icon" onClick={onStepBackward} title={t("Bir adım geri")} aria-label={t("Bir adım geri")}>
          <SkipBack size={15} />
        </button>
        <button id="btn-replay-play" className={`rw-btn rw-btn-icon ${isPlaying ? "is-on" : ""}`} onClick={onTogglePlay} title={isPlaying ? t("Duraklat") : t("Oynat")} aria-label={isPlaying ? t("Duraklat") : t("Oynat")}>
          {isPlaying ? <Pause size={15} /> : <Play size={15} />}
        </button>
        <button id="btn-replay-next" className="rw-btn rw-btn-icon" onClick={onStepForward} title={t("Bir adım ileri")} aria-label={t("Bir adım ileri")}>
          <SkipForward size={15} />
        </button>
      </div>
      <div className="rw-time">
        <span>{currentSimTime.toFixed(2)} {t("sn")}</span>
        <span className="dim"> / {totalDuration.toFixed(2)} {t("sn")}</span>
      </div>
      <div className="rw-btn-group" aria-label={t("Oynatma hızı")}>
        {[0.5, 1.0, 2.0].map((s) => (
          <button
            key={s}
            className={`rw-btn rw-btn-sm mono ${speed === s ? "rw-btn-primary" : "rw-btn-ghost"}`}
            onClick={() => onSpeedChange(s)}
            title={`${s}× ${t("hızla oynat")}`}
          >
            {s}×
          </button>
        ))}
      </div>
    </div>
  );
};
