"use client";

import React from "react";
import { useLocale } from "../lib/i18n";
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

export const REASON_LABELS_EN: Record<string, string> = {
  COLLISION: "Collision",
  MIN_CLEARANCE_VIOLATION: "Safety clearance violated",
  GOAL_NOT_REACHED: "Goal not reached",
  TIMEOUT: "Timeout",
  STUCK: "Robot got stuck",
  MISSING_TELEMETRY: "No telemetry recorded",
  INCOMPLETE_EVALUATION: "Evaluation incomplete",
};

interface RunVerdictProps {
  result: RunResult;
  minClearanceLimitM?: number;
}

/** Independent-oracle verdict for a finished run: crash or not, in plain terms. */
export const RunVerdict: React.FC<RunVerdictProps> = ({ result, minClearanceLimitM }) => {
  const { locale, t } = useLocale();
  const reasons = (codes: string[]) =>
    codes
      .map((c) => (locale === "en" ? (REASON_LABELS_EN[c] ?? c) : (REASON_LABELS[c] ?? c)))
      .join(" · ");
  const m = result.metrics;
  if (result.oracle_status === "PASS") {
    return (
      <div className="rw-verdict is-solid" role="status">
        <span className="rw-verdict-label">{t("Çalıştırma sonucu — bağımsız kontrol")}</span>
        <span className="rw-verdict-value">{t("KAZASIZ TAMAMLANDI ✓")}</span>
        <span className="rw-verdict-sub">
          {t("Çarpışma yok, hedefe ulaşıldı. En düşük engel mesafesi")} {m.min_clearance_m} m
          {minClearanceLimitM !== undefined ? ` (${t("sınır:")} ${minClearanceLimitM} m)` : ""} ·{" "}
          {t("Süre")} {m.sim_duration_s} {t("sn")}
        </span>
      </div>
    );
  }
  if (result.oracle_status === "FAIL") {
    const nearMiss =
      !m.collision_detected &&
      m.goal_reached &&
      result.reason_codes.includes("MIN_CLEARANCE_VIOLATION");
    return (
      <div className="rw-verdict is-fail" role="status">
        <span className="rw-verdict-label">{t("Çalıştırma sonucu — bağımsız kontrol")}</span>
        <span className="rw-verdict-value">
          {m.collision_detected
            ? t("KAZA OLDU ✗")
            : nearMiss
              ? t("HEDEFE ULAŞTI AMA GÜVENLİ DEĞİL ✗")
              : t("BAŞARISIZ ✗")}
        </span>
        <span className="rw-verdict-sub">
          {nearMiss ? (
            <>
              {t("Çarpışma olmadı ve robot hedefe ulaştı; ancak engele en yakın")}{" "}
              <strong>{m.min_clearance_m} m</strong> {t("mesafeden geçti.")}
              {minClearanceLimitM !== undefined ? (
                <>
                  {" "}
                  {t("İzin verilen en düşük güvenli mesafe")} <strong>{minClearanceLimitM} m</strong>{" "}
                  {t("olduğu için test başarısız sayıldı.")}
                </>
              ) : (
                <> {t("İzin verilen en düşük güvenli mesafenin altına inildiği için test başarısız sayıldı.")}</>
              )}{" "}
              {t("Buna “yakın geçiş” denir; 2. adımda bu yakın geçiş incelenir.")}
            </>
          ) : (
            <>
              {reasons(result.reason_codes) || t("Kural ihlali")} · {t("En düşük mesafe")}{" "}
              {m.min_clearance_m} m · {t("Hedefe")} {m.goal_reached ? t("ulaşıldı") : t("ulaşılamadı")} ·{" "}
              {t("Süre")} {m.sim_duration_s} {t("sn")}
            </>
          )}
        </span>
      </div>
    );
  }
  return (
    <div className="rw-verdict" role="status">
      <span className="rw-verdict-label">{t("Çalıştırma sonucu — bağımsız kontrol")}</span>
      <span className="rw-verdict-value">{t("KARAR VERİLEMEDİ")}</span>
      <span className="rw-verdict-sub">
        {t("Ölçümler sonucu belirlemeye yetmedi:")} {reasons(result.reason_codes)}
      </span>
    </div>
  );
};
