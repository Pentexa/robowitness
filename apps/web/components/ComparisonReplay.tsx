"use client";

import React, { useEffect, useState } from "react";
import { ReplayControls } from "./ReplayControls";
import { SimulationCanvas } from "./SimulationCanvas";
import { fetchAllFrames, fetchCandidateTelemetry, fetchTelemetry } from "../lib/api";
import { useLocale } from "../lib/i18n";
import { GateResult, ScenarioSpec, TelemetryFrame } from "../lib/types";

interface ComparisonReplayProps {
  scenario: ScenarioSpec | null;
  baselineRunId: string;
  verificationId: string;
  gates: GateResult[];
}

const boolLabel = (v: unknown, yes: string, no: string): string =>
  v === true || v === "true" ? yes : v === false || v === "false" ? no : String(v ?? "—");

export const ComparisonReplay: React.FC<ComparisonReplayProps> = ({
  scenario,
  baselineRunId,
  verificationId,
  gates,
}) => {
  const { t } = useLocale();
  const [baseFrames, setBaseFrames] = useState<TelemetryFrame[]>([]);
  const [candFrames, setCandFrames] = useState<TelemetryFrame[]>([]);
  const [index, setIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [speed, setSpeed] = useState<number>(1.0);
  const [status, setStatus] = useState<string>("loading");

  useEffect(() => {
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
  }, [baselineRunId, verificationId]);

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

  const paired = gates.find((g) => g.gate_id === "GATE_2_PAIRED");
  const baseIdx = Math.min(index, Math.max(0, baseFrames.length - 1));
  const candIdx = Math.min(index, Math.max(0, candFrames.length - 1));

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">{t("Eski ve Yeni Ayarlar Yan Yana")}</h3>
          <p className="rw-card-sub">{t("İkisi de birebir aynı testte çalıştı. Solda eski, sağda yeni ayarlar.")}</p>
        </div>
        <span className="rw-badge mono">
          {status === "ready" ? `${t("ESKİ")} ${baseFrames.length} / ${t("YENİ")} ${candFrames.length} ${t("ADIM")}` : t("HAZIRLANIYOR")}
        </span>
      </div>
      <div className="rw-card-body">
        {status === "loading" && <p className="rw-empty">{t("İki çalıştırma da yükleniyor…")}</p>}
        {status === "no-candidate" && (
          <p className="rw-empty">{t("Bu kayıtta yeni ayarların tekrar görüntüsü yok. Kontrol sonuçları yine de geçerlidir.")}</p>
        )}
        {status.startsWith("error") && <p className="rw-err">{t("Yüklenemedi:")} {status}</p>}
        {status === "ready" && (
          <>
            {paired && (
              <p className="mono text-xs muted">
                {t("Engele en yakın mesafe:")} {String(paired.details.baseline_min_clearance_m)} m →{" "}
                {String(paired.details.candidate_min_clearance_m)} m · {t("Hedefe ulaştı mı:")}{" "}
                {boolLabel(paired.details.baseline_goal_reached, t("Evet"), t("Hayır"))} → {boolLabel(paired.details.candidate_goal_reached, t("Evet"), t("Hayır"))}
              </p>
            )}
            <div className="rw-compare">
              <div>
                <h4>{t("Eski ayarlar")} · {t("adım")} {baseFrames[baseIdx]?.tick ?? 0}</h4>
                <SimulationCanvas scenario={scenario} frames={baseFrames} currentFrameIndex={baseIdx} />
              </div>
              <div>
                <h4>{t("Yeni ayarlar")} · {t("adım")} {candFrames[candIdx]?.tick ?? 0}</h4>
                <SimulationCanvas scenario={scenario} frames={candFrames} currentFrameIndex={candIdx} />
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
            <details className="rw-details">
              <summary>{t("Teknik detaylar (isteğe bağlı)")}</summary>
              <div>
                <span className="mono text-xs">
                  {t("Eski çalıştırma:")} {baselineRunId} · {t("Kayıt:")} {verificationId}
                </span>
              </div>
            </details>
          </>
        )}
      </div>
    </div>
  );
};
