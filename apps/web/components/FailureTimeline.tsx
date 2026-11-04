"use client";

import React, { useMemo } from "react";
import { useLocale } from "../lib/i18n";
import { TelemetryFrame } from "../lib/types";

interface FailureTimelineProps {
  frames: TelemetryFrame[];
  currentIndex: number;
  onSeek: (index: number) => void;
  minClearanceLimitM?: number;
}

const EVENT_STYLE: Record<string, { color: string; label: string }> = {
  COLLISION: { color: "#b3261e", label: "COLLISION" },
  GOAL_REACHED: { color: "#1e7d32", label: "GOAL" },
  STUCK: { color: "#e07b00", label: "STUCK" },
  TIMEOUT: { color: "#6a1b9a", label: "TIMEOUT" },
  CLEARANCE_WARNING: { color: "#c9a227", label: "CLEARANCE" },
  MIN_CLEARANCE_VIOLATION: { color: "#b3261e", label: "VIOLATION" },
};

/**
 * Failure timeline: measured clearance, sensor age (delay), the safety
 * threshold, and failure events on one axis, synchronized with the replay.
 * Clicking anywhere seeks the replay to that tick. Display only — the
 * oracle's verdict never comes from this chart.
 */
export const FailureTimeline: React.FC<FailureTimelineProps> = ({
  frames,
  currentIndex,
  onSeek,
  minClearanceLimitM,
}) => {
  const { t } = useLocale();
  const W = 720;
  const H = 190;
  const PAD = 30;

  const model = useMemo(() => {
    if (frames.length === 0) return null;
    const maxClear = Math.max(0.5, ...frames.map((f) => f.clearance_m));
    const maxAge = Math.max(0.05, ...frames.map((f) => f.sensor.age_s));
    const n = frames.length;
    const x = (i: number) => PAD + (i / Math.max(n - 1, 1)) * (W - 2 * PAD);
    const yClear = (v: number) => H - PAD - (v / maxClear) * (H - 2 * PAD);
    const yAge = (v: number) => H - PAD - (v / maxAge) * (H - 2 * PAD);
    const clearPts = frames.map((f, i) => `${x(i).toFixed(1)},${yClear(f.clearance_m).toFixed(1)}`).join(" ");
    const agePts = frames.map((f, i) => `${x(i).toFixed(1)},${yAge(f.sensor.age_s).toFixed(1)}`).join(" ");
    const events: Array<{ i: number; type: string }> = [];
    frames.forEach((f, i) => {
      for (const e of f.events) {
        if (EVENT_STYLE[e.type]) events.push({ i, type: e.type });
      }
    });
    return { maxClear, maxAge, x, yClear, clearPts, agePts, events };
  }, [frames]);

  if (!model || frames.length <= 1) return null;
  const cur = frames[Math.min(currentIndex, frames.length - 1)];
  const curX = model.x(Math.min(currentIndex, frames.length - 1));

  const handleClick = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / Math.max(rect.width, 1);
    const svgX = ratio * W;
    const idx = Math.round(((svgX - PAD) / (W - 2 * PAD)) * (frames.length - 1));
    onSeek(Math.max(0, Math.min(frames.length - 1, idx)));
  };

  return (
    <div className="rw-card rw-failure-timeline">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">{t("Arıza Zaman Çizgisi")}</h3>
          <p className="rw-card-sub">
            {t("Ölçülen mesafe, sensör gecikmesi, güvenlik eşiği ve olaylar tek eksende; tıkladığınız ana tekrar senkronize olur.")}
          </p>
        </div>
        <span className="rw-badge mono">
          {t("ADIM")} {cur?.tick ?? 0} · {t("mesafe")} {(cur?.clearance_m ?? 0).toFixed(3)} m ·{" "}
          {t("gecikme")} {((cur?.sensor.age_s ?? 0) * 1000).toFixed(0)} ms
        </span>
      </div>
      <div className="rw-card-body">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="rw-timeline-chart"
          onClick={handleClick}
          role="img"
          aria-label={t("Arıza zaman çizgisi grafiği")}
        >
          <rect x={0} y={0} width={W} height={H} fill="#fff" />
          {minClearanceLimitM !== undefined && (
            <>
              <line
                x1={PAD}
                x2={W - PAD}
                y1={model.yClear(minClearanceLimitM)}
                y2={model.yClear(minClearanceLimitM)}
                stroke="#b3261e"
                strokeDasharray="5 4"
                strokeWidth={1.4}
              />
              <text x={W - PAD} y={model.yClear(minClearanceLimitM) - 5} fontSize={10} fill="#b3261e" textAnchor="end">
                {t("güvenlik eşiği")} {minClearanceLimitM.toFixed(2)} m
              </text>
            </>
          )}
          <polyline points={model.agePts} fill="none" stroke="#8a8f98" strokeWidth={1.2} />
          <polyline points={model.clearPts} fill="none" stroke="#1c4fd8" strokeWidth={1.6} />
          {model.events.map((ev, k) => (
            <g key={k}>
              <line
                x1={model.x(ev.i)}
                x2={model.x(ev.i)}
                y1={PAD - 8}
                y2={H - PAD}
                stroke={EVENT_STYLE[ev.type].color}
                strokeWidth={1.2}
                opacity={0.65}
              />
              <circle cx={model.x(ev.i)} cy={PAD - 10} r={4} fill={EVENT_STYLE[ev.type].color} />
              <text x={model.x(ev.i)} y={PAD - 18} fontSize={9} fill={EVENT_STYLE[ev.type].color} textAnchor="middle">
                {EVENT_STYLE[ev.type].label}
              </text>
            </g>
          ))}
          <line x1={curX} x2={curX} y1={PAD - 8} y2={H - PAD} stroke="#111" strokeWidth={1.6} />
          <text x={PAD} y={14} fontSize={10} fill="#1c4fd8">{t("mesafe")}</text>
          <text x={PAD + 52} y={14} fontSize={10} fill="#8a8f98">{t("sensör gecikmesi")}</text>
          <text x={PAD} y={H - 8} fontSize={10} fill="#666">{t("zaman (adım)")} →</text>
        </svg>
        <div className="rw-marks-legend">
          {Object.entries(EVENT_STYLE).map(([type, s]) => (
            <span key={type} className="rw-legend-item">
              <span className="rw-legend-dot" style={{ background: s.color }} /> {s.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
