"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createAdversarialTest,
  fetchAdversarialTest,
  fetchAdversarialTests,
  fetchJob,
} from "../lib/api";
import { useLocale } from "../lib/i18n";
import { AdversarialResult, PolicyConfig } from "../lib/types";

interface AdversarialPanelProps {
  policy: PolicyConfig;
  seedRunId?: string | null;
  disabled?: boolean;
}

/**
 * Adversarial rounds: Muse Spark (live) or the offline reference adapter
 * proposes challenging scenarios; each executed one is a real run judged by
 * the oracle. The AI proposes — it never decides. Bounded by a strict
 * iteration cap (server-side, hard max 10).
 */
export const AdversarialPanel: React.FC<AdversarialPanelProps> = ({
  policy,
  seedRunId,
  disabled,
}) => {
  const { t } = useLocale();
  const [iterations, setIterations] = useState(3);
  const [result, setResult] = useState<AdversarialResult | null>(null);
  const [history, setHistory] = useState<AdversarialResult[]>([]);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchAdversarialTests(5)
      .then(setHistory)
      .catch(() => console.warn("Adversarial history unavailable"));
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const handleRun = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const queued = await createAdversarialTest({
        policy,
        max_iterations: iterations,
        seed_run_id: seedRunId ?? null,
      });
      timerRef.current = setInterval(async () => {
        try {
          const job = await fetchJob(queued.job_id);
          if (job.status === "completed") {
            if (timerRef.current) clearInterval(timerRef.current);
            const done = await fetchAdversarialTest(queued.result_id);
            setResult(done);
            setHistory((prev) => [done, ...prev].slice(0, 5));
            setRunning(false);
          } else if (job.status === "failed" || job.status === "cancelled") {
            if (timerRef.current) clearInterval(timerRef.current);
            setError(t("Rakip testi işi başarısız oldu."));
            setRunning(false);
          }
        } catch {
          /* keep polling */
        }
      }, 1500);
    } catch {
      setError(t("Rakip testi başlatılamadı."));
      setRunning(false);
    }
  };

  const renderResult = (data: AdversarialResult) => (
    <div>
      <table className="rw-table">
        <thead>
          <tr>
            <th>#</th>
            <th>{t("Senaryo")}</th>
            <th>{t("Kaynak")}</th>
            <th>{t("Sonuç")}</th>
            <th>{t("En düşük mesafe")}</th>
          </tr>
        </thead>
        <tbody>
          {data.rounds.map((r) => (
            <tr key={r.iteration}>
              <td>{r.iteration}</td>
              <td className="mono">{r.scenario_id ?? "—"}</td>
              <td>{r.provenance}</td>
              <td>
                {r.executed
                  ? `${r.oracle_status ?? ""} (${r.reason_codes.join(", ") || "—"})`
                  : t(r.note === "duplicate_scenario_not_rerun" ? "Aynı senaryo tekrar koşulmadı" : "Çalıştırılmadı")}
              </td>
              <td>{r.min_clearance_m !== null ? `${r.min_clearance_m.toFixed(3)} m` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="rw-hint">
        {t("Çalıştırılan")}: {data.executed_count} · {t("FAIL")}: {data.fail_count} ·{" "}
        {t("PASS")}: {data.pass_count} · {t("Durma nedeni")}: {data.stopped_reason}
        {data.total_tokens_used > 0 ? ` · ${t("Token")}: ${data.total_tokens_used}` : ""}
      </p>
    </div>
  );

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">{t("AI Rakip Testi")}</h3>
          <p className="rw-card-sub">
            {t("Meta AI, önceki başarısızlıklardan beslenerek zorlayıcı senaryolar önerir; her biri gerçek koşumla ve oracle ile yargılanır. AI önerir, kararı oracle verir.")}
          </p>
        </div>
        <span className="rw-badge mono">{t("SINIRLI")}</span>
      </div>
      <div className="rw-card-body">
        <div className="rw-field">
          <span>{t("Tur sayısı (en fazla 5, sert tavan 10)")}</span>
          <input
            id="input-adversarial-iterations"
            className="rw-input"
            type="number"
            min={1}
            max={5}
            value={iterations}
            onChange={(e) => setIterations(Math.max(1, Math.min(5, Number(e.target.value) || 1)))}
            disabled={running}
          />
        </div>
        <button
          id="btn-run-adversarial"
          type="button"
          className="rw-btn rw-btn-primary rw-btn-block"
          onClick={handleRun}
          disabled={disabled || running}
        >
          {running ? t("Rakip testi çalışıyor…") : t("Rakip Testini Başlat")}
        </button>
        {error && <p className="rw-err">{error}</p>}
        {result && renderResult(result)}
        {history.length > 0 && (
          <details className="rw-details">
            <summary>{t("Önceki rakip testleri")}</summary>
            {history.map((h) => (
              <button key={h.adversarial_id} type="button" className="rw-linklike" onClick={() => setResult(h)}>
                {h.executed_count} {t("koşum")} · {h.fail_count} FAIL ·{" "}
                {new Date(h.created_at).toLocaleString()}
              </button>
            ))}
          </details>
        )}
      </div>
    </div>
  );
};
