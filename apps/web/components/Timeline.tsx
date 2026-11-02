"use client";

import React from "react";
import { useLocale } from "../lib/i18n";
import { TelemetryFrame } from "../lib/types";

interface TimelineProps {
  frames: TelemetryFrame[];
  currentIndex: number;
  onSeek: (index: number) => void;
}

export const Timeline: React.FC<TimelineProps> = ({ frames, currentIndex, onSeek }) => {
  const { t } = useLocale();
  const total = frames.length;
  if (total <= 1) return null;

  const collisionFrames = frames
    .map((f, i) => (f.events.some((e) => e.type === "COLLISION") ? i : -1))
    .filter((i) => i >= 0);
  const cur = frames[Math.min(currentIndex, total - 1)];

  return (
    <div className="rw-timeline">
      <input
        id="timeline-scrubber"
        type="range"
        min={0}
        max={total - 1}
        value={Math.min(currentIndex, total - 1)}
        onChange={(e) => onSeek(parseInt(e.target.value, 10))}
        className="rw-range"
        aria-label={t("Zaman çizgisi: kaydırarak istediğiniz ana gidin")}
      />
      <div className="rw-marks">
        {collisionFrames.map((idx) => (
          <span
            key={idx}
            className="rw-mark-hit"
            style={{ left: `${(idx / (total - 1)) * 100}%` }}
            title={`${t("Çarpma anı")} (${frames[idx]?.tick ?? idx}. ${t("adım")})`}
          />
        ))}
      </div>
      <div className="rw-stats">
        <span>{t("ADIM")} {cur?.tick ?? 0} / {total - 1}</span>
        <span>{t("ENGELE MESAFE")} {(cur?.clearance_m ?? 0).toFixed(3)} m</span>
        <span>{t("HIZ")} {(cur?.command.linear_mps ?? 0).toFixed(2)} m/{t("sn")}</span>
      </div>
    </div>
  );
};
