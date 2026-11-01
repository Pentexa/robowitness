"use client";

import React from "react";
import { RunResult } from "../lib/types";

export const REASON_LABELS: Record<string, string> = {
  COLLISION: "Çarpışma oldu",
  MIN_CLEARANCE_VIOLATION: "Güvenli mesafe aşıldı",
  GOAL_NOT_REACHED: "Hedefe ulaşılamadı",
  TIMEOUT: "Süre doldu",
  STUCK: "Robot takılı kaldı",
  MISSING_TELEMETRY: "Ölçüm kaydı yok",
  INCOMPLETE_EVALUATION: "Değerlendirme tamamlanamadı",
};

interface RunVerdictProps {
  result: RunResult;
  minClearanceLimitM?: number;
}

/** Independent-oracle verdict for a finished run: crash or not, in plain terms. */
export const RunVerdict: React.FC<RunVerdictProps> = ({ result, minClearanceLimitM }) => {
  const m = result.metrics;
  if (result.oracle_status === "PASS") {
    return (
      <div className="rw-verdict is-solid" role="status">
        <span className="rw-verdict-label">Çalıştırma sonucu — bağımsız kontrol</span>
        <span className="rw-verdict-value">KAZASIZ TAMAMLANDI ✓</span>
        <span className="rw-verdict-sub">
          Çarpışma yok, hedefe ulaşıldı. En düşük engel mesafesi {m.min_clearance_m} m
          {minClearanceLimitM !== undefined ? ` (sınır: ${minClearanceLimitM} m)` : ""} · Süre{" "}
          {m.sim_duration_s} sn
        </span>
      </div>
    );
  }
  if (result.oracle_status === "FAIL") {
    // Near-miss: no crash and goal reached, but the robot passed closer to an
    // obstacle than the allowed safety distance. This looks like success on
    // screen, so it must be spelled out, not just labeled "failure".
    const nearMiss =
      !m.collision_detected &&
      m.goal_reached &&
      result.reason_codes.includes("MIN_CLEARANCE_VIOLATION");
    return (
      <div className="rw-verdict is-fail" role="status">
        <span className="rw-verdict-label">Çalıştırma sonucu — bağımsız kontrol</span>
        <span className="rw-verdict-value">
          {m.collision_detected
            ? "KAZA OLDU ✗"
            : nearMiss
              ? "HEDEFE ULAŞTI AMA GÜVENLİ DEĞİL ✗"
              : "BAŞARISIZ ✗"}
        </span>
        <span className="rw-verdict-sub">
          {nearMiss ? (
            <>
              Çarpışma olmadı ve robot hedefe ulaştı; ancak engele en yakın{" "}
              <strong>{m.min_clearance_m} m</strong> mesafeden geçti.
              {minClearanceLimitM !== undefined ? (
                <>
                  {" "}
                  İzin verilen en düşük güvenli mesafe <strong>{minClearanceLimitM} m</strong> olduğu
                  için test başarısız sayıldı.
                </>
              ) : (
                <> İzin verilen en düşük güvenli mesafenin altına inildiği için test başarısız sayıldı.</>
              )}{" "}
              Buna “yakın geçiş” denir; 2. adımda bu yakın geçiş incelenir.
            </>
          ) : (
            <>
              {result.reason_codes.map((c) => REASON_LABELS[c] ?? c).join(" · ") || "Kural ihlali"}
              {" · "}En düşük mesafe {m.min_clearance_m} m · Hedefe{" "}
              {m.goal_reached ? "ulaşıldı" : "ulaşılamadı"} · Süre {m.sim_duration_s} sn
            </>
          )}
        </span>
      </div>
    );
  }
  return (
    <div className="rw-verdict" role="status">
      <span className="rw-verdict-label">Çalıştırma sonucu — bağımsız kontrol</span>
      <span className="rw-verdict-value">KARAR VERİLEMEDİ</span>
      <span className="rw-verdict-sub">
        Ölçümler sonucu belirlemeye yetmedi:{" "}
        {result.reason_codes.map((c) => REASON_LABELS[c] ?? c).join(" · ")}
      </span>
    </div>
  );
};
