"use client";

import React, { useEffect, useMemo, useState } from "react";
import { ReplayControls } from "./ReplayControls";
import { SimulationCanvas } from "./SimulationCanvas";
import { fetchAllFrames, fetchCandidateTelemetry, fetchTelemetry } from "../lib/api";
import { useLocale } from "../lib/i18n";
import { ScenarioSpec, TelemetryFrame, VerificationRecord } from "../lib/types";

interface PixelProofProps {
  scenario: ScenarioSpec | null;
  verification: VerificationRecord | null;
}

const fmt = (v: number | null | undefined): string =>
  v === null || v === undefined || Number.isNaN(v) ? "—" : v.toFixed(4);

function minClearance(frames: TelemetryFrame[]): number | null {
  if (frames.length === 0) return null;
  return frames.reduce((m, f) => Math.min(m, f.clearance_m), Number.POSITIVE_INFINITY);
}

/**
 * Pixel Proof: the visual evidence layer over Gate 2's paired replay.
 * It is NOT a sixth gate and never changes a verdict — every number shown
 * is read from the sealed pair (gate details first, measured telemetry
 * second). Without a completed verification it says so, plainly.
 */
export const PixelProof: React.FC<PixelProofProps> = ({ scenario, verification }) => {
  const { t } = useLocale();
  const [baseFrames, setBaseFrames] = useState<TelemetryFrame[]>([]);
  const [candFrames, setCandFrames] = useState<TelemetryFrame[]>([]);
  const [index, setIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1.0);
  const [status, setStatus] = useState<string>("idle");

  const verificationId = verification?.verification_id ?? null;
  const baselineRunId = verification?.baseline_run_id ?? null;

  useEffect(() => {
    if (!verificationId || !baselineRunId) {
      setStatus("idle");
      setBaseFrames([]);
      setCandFrames([]);
      return;
    }
    let cancelled = false;
    setStatus("loading");
    Promise.all([
      fetchAllFrames((o, l) => fetchTelemetry(baselineRunId, o, l)),
      fetchAllFrames((o, l) => fetchCandidateTelemetry(verificationId, o, l)),
    ])
      .then(([b, c]) => {
        if (cancelled) return;
        setBaseFrames(b);
        setCandFrames(c);
        setIndex(0);
        setStatus("ready");
      })
      .catch((e: Error) => {
        if (cancelled) return;
        setStatus(e.message === "CANDIDATE_REPLAY_MISSING" ? "no-candidate" : `error: ${e.message}`);
      });
    return () => {
      cancelled = true;
    };
  }, [verificationId, baselineRunId]);

  useEffect(() => {
    if (!isPlaying) return;
    const maxLen = Math.max(baseFrames.length, candFrames.length);
    if (maxLen === 0) return;
    const timer = setInterval(() => {
      setIndex((prev) => {
        if (prev >= maxLen - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, 1000 / 60 / speed);
    return () => clearInterval(timer);
  }, [isPlaying, speed, baseFrames.length, candFrames.length]);

  const paired = verification?.gates.find((g) => g.gate_id === "GATE_2_PAIRED");
  const baseMin = useMemo(() => {
    const fromGate = paired?.details?.baseline_min_clearance_m;
    return typeof fromGate === "number" ? fromGate : minClearance(baseFrames);
  }, [paired, baseFrames]);
  const candMin = useMemo(() => {
    const fromGate = paired?.details?.candidate_min_clearance_m;
    return typeof fromGate === "number" ? fromGate : minClearance(candFrames);
  }, [paired, candFrames]);

  const limit = scenario?.oracle.min_clearance_m ?? null;
  const baseIdx = Math.min(index, Math.max(0, baseFrames.length - 1));
  const candIdx = Math.min(index, Math.max(0, candFrames.length - 1));
  const baseNow = baseFrames[baseIdx]?.clearance_m ?? null;
  const candNow = candFrames[candIdx]?.clearance_m ?? null;
  const delta = baseMin !== null && candMin !== null ? candMin - baseMin : null;

  const liveBadge = (value: number | null) => {
    const danger = value !== null && limit !== null && value < limit;
    return (
      <span className={`rw-pixel-live ${danger ? "is-danger" : "is-safe"}`}>
        {t("Şu anki mesafe")}: {fmt(value)} m
      </span>
    );
  };

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">{t("Piksel Kanıt")}</h3>
          <p className="rw-card-sub">
            {t("Piksel kanıt, beş kapının görsel katmanıdır; altıncı kapı değildir ve kararı değiştirmez — kararı gösterir.")}
          </p>
        </div>
      </div>
      <div className="rw-card-body">
        {!verification && (
          <p className="rw-empty">
            {t("Piksel kanıt için tamamlanmış bir doğrulama gerekli. Önce bir düzeltmeyi doğrulayın; eski ve yeni koşum burada yan yana, ölçülen mesafelerle gösterilir.")}
          </p>
        )}
        {verification && status === "loading" && <p className="rw-empty">{t("Piksel kanıt yükleniyor…")}</p>}
        {verification && status === "no-candidate" && (
          <p className="rw-empty">{t("Bu kayıtta yeni ayarların tekrar görüntüsü yok. Kontrol sonuçları yine de geçerlidir.")}</p>
        )}
        {verification && status.startsWith("error") && (
          <p className="rw-err">{t("Yüklenemedi:")} {status}</p>
        )}
        {verification && status === "ready" && (
          <>
            <div className="rw-pixel-band" role="status">
              <span className="rw-pixel-min is-base">
                {t("Eski ayarlar")} · {t("Ölçülen en düşük mesafe")}: {fmt(baseMin)} m
              </span>
              <span className="rw-pixel-arrow">→</span>
              <span className="rw-pixel-min is-cand">
                {t("Yeni ayarlar")} · {t("Ölçülen en düşük mesafe")}: {fmt(candMin)} m
              </span>
              {delta !== null && (
                <span className="rw-pixel-delta mono">
                  Δ {delta >= 0 ? "+" : ""}{delta.toFixed(4)} m
                </span>
              )}
            </div>
            <div className="rw-compare">
              <div>
                <h4>{t("Eski ayarlar")} · {t("adım")} {baseFrames[baseIdx]?.tick ?? 0}</h4>
                <div className="rw-pixel-wrap">
                  <SimulationCanvas scenario={scenario} frames={baseFrames} currentFrameIndex={baseIdx} />
                  {liveBadge(baseNow)}
                </div>
              </div>
              <div>
                <h4>{t("Yeni ayarlar")} · {t("adım")} {candFrames[candIdx]?.tick ?? 0}</h4>
                <div className="rw-pixel-wrap">
                  <SimulationCanvas scenario={scenario} frames={candFrames} currentFrameIndex={candIdx} />
                  {liveBadge(candNow)}
                </div>
              </div>
            </div>
            <ReplayControls
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying(!isPlaying)}
              onReset={() => {
                setIsPlaying(false);
                setIndex(0);
              }}
              onStepForward={() => setIndex((p) => Math.min(Math.max(baseFrames.length, candFrames.length) - 1, p + 1))}
              onStepBackward={() => setIndex((p) => Math.max(0, p - 1))}
              speed={speed}
              onSpeedChange={setSpeed}
              currentSimTime={baseFrames[baseIdx]?.sim_time_s ?? 0}
              totalDuration={baseFrames[baseFrames.length - 1]?.sim_time_s ?? 0}
            />
          </>
        )}
      </div>
    </div>
  );
};
