"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  createStressTest,
  fetchJob,
  fetchStressTests,
  fetchStressTest,
} from "../lib/api";
import { useLocale } from "../lib/i18n";
import { PolicyConfig, ScenarioSpec, StressTestResult } from "../lib/types";

interface StressPanelProps {
  scenario: ScenarioSpec | null;
  policy: PolicyConfig;
  disabled?: boolean;
}

const LATENCY_OPTIONS = [0, 150, 300, 450, 600, 900];
const NOISE_OPTIONS = [0, 0.01, 0.03, 0.05, 0.1];

function cellClass(cell: { oracle_status: string; near_miss: boolean }): string {
  if (cell.oracle_status === "PASS") return "is-pass";
  if (cell.near_miss) return "is-near";
  if (cell.oracle_status === "FAIL") return "is-fail";
  return "is-unknown";
}

/**
 * Sensor stress test: the selected scenario is re-run on a latency x noise
 * grid. Every cell is a real recorded run judged by the same oracle; the
 * heatmap only visualizes measured outcomes.
 */
export const StressPanel: React.FC<StressPanelProps> = ({ scenario, policy, disabled }) => {
  const { t } = useLocale();
  const [latencies, setLatencies] = useState<number[]>([0, 300, 600]);
  const [noises, setNoises] = useState<number[]>([0, 0.03, 0.1]);
  const [result, setResult] = useState<StressTestResult | null>(null);
  const [history, setHistory] = useState<StressTestResult[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchStressTests(5)
      .then(setHistory)
      .catch(() => console.warn("Stress history unavailable"));
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const toggle = (list: number[], value: number, setter: (v: number[]) => void) => {
    setter(list.includes(value) ? list.filter((v) => v !== value) : [...list, value].sort((a, b) => a - b));
  };

  const cellCount = latencies.length * noises.length;
  const tooLarge = cellCount > 40;

  const handleRun = async () => {
    if (!scenario || tooLarge || latencies.length === 0 || noises.length === 0) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const queued = await createStressTest({
        scenario,
        policy,
        latencies_ms: latencies,
        noise_levels_m: noises,
      });
      timerRef.current = setInterval(async () => {
        try {
          const job = await fetchJob(queued.job_id);
          const pct = (job as { progress?: { pct?: number } | null }).progress?.pct;
          setProgress(pct !== undefined ? `%${Math.round(pct)}` : null);
          if (job.status === "completed") {
            if (timerRef.current) clearInterval(timerRef.current);
            const done = await fetchStressTest(queued.result_id);
            setResult(done);
            setHistory((prev) => [done, ...prev].slice(0, 5));
            setRunning(false);
            setProgress(null);
          } else if (job.status === "failed" || job.status === "cancelled") {
            if (timerRef.current) clearInterval(timerRef.current);
            setError(t("Stres testi işi başarısız oldu."));
            setRunning(false);
            setProgress(null);
          }
        } catch {
          /* keep polling */
        }
      }, 1500);
    } catch {
      setError(t("Stres testi başlatılamadı."));
      setRunning(false);
    }
  };

  const renderHeatmap = (data: StressTestResult) => {
    const byKey = new Map(data.cells.map((c) => [`${c.latency_ms}|${c.noise_std_m}`, c]));
    return (
      <div className="rw-heatmap-wrap">
        <table className="rw-heatmap" aria-label={t("Stres testi ısı haritası")}>
          <thead>
            <tr>
              <th>{t("Gecikme")} \ {t("Gürültü")}</th>
              {data.noise_levels_m.map((n) => (
                <th key={n}>{n.toFixed(2)} m</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.latencies_ms.map((lat) => (
              <tr key={lat}>
                <th>{lat} ms</th>
                {data.noise_levels_m.map((n) => {
                  const cell = byKey.get(`${lat}|${n}`);
                  if (!cell) return <td key={n}>—</td>;
                  return (
                    <td
                      key={n}
                      className={cellClass(cell)}
                      title={`${cell.oracle_status} · ${cell.reason_codes.join(", ") || "—"} · ${cell.run_id}`}
                    >
                      {cell.oracle_status}
                      <span className="rw-heat-min">{cell.metrics.min_clearance_m.toFixed(3)} m</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="rw-hint">
          {t("Özet")}: {data.summary.passed}/{data.summary.total} {t("geçti")} ·{" "}
          {data.summary.failed} {t("kaldı")} · {data.summary.near_misses}{" "}
          {t("yakın ıska")} · {t("en düşük mesafe")}{" "}
          {data.summary.worst_clearance_m?.toFixed(3) ?? "—"} m
        </p>
      </div>
    );
  };

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">{t("Sensör Stres Testi")}</h3>
          <p className="rw-card-sub">
            {t("Seçili senaryo, gecikme × gürültü ızgarasında yeniden koşulur; her hücre gerçek bir koşumdur ve aynı oracle tarafından yargılanır.")}
          </p>
        </div>
      </div>
      <div className="rw-card-body">
        {!scenario && <p className="rw-empty">{t("Önce bir senaryo seçin.")}</p>}
        {scenario && (
          <>
            <div className="rw-field">
              <span>{t("Sensör gecikmesi (ms)")}</span>
              <div className="rw-chip-row">
                {LATENCY_OPTIONS.map((v) => (
                  <button
                    key={v}
                    type="button"
                    className={`rw-chip ${latencies.includes(v) ? "is-on" : ""}`}
                    onClick={() => toggle(latencies, v, setLatencies)}
                    disabled={running}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
            <div className="rw-field">
              <span>{t("Sensör gürültüsü (m)")}</span>
              <div className="rw-chip-row">
                {NOISE_OPTIONS.map((v) => (
                  <button
                    key={v}
                    type="button"
                    className={`rw-chip ${noises.includes(v) ? "is-on" : ""}`}
                    onClick={() => toggle(noises, v, setNoises)}
                    disabled={running}
                  >
                    {v.toFixed(2)}
                  </button>
                ))}
              </div>
            </div>
            {tooLarge && <p className="rw-err">{t("Izgara en fazla 40 hücre olabilir.")}</p>}
            <button
              id="btn-run-stress"
              type="button"
              className="rw-btn rw-btn-primary rw-btn-block"
              onClick={handleRun}
              disabled={disabled || running || tooLarge || latencies.length === 0 || noises.length === 0}
            >
              {running
                ? `${t("Stres testi çalışıyor…")} ${progress ?? ""}`
                : `${t("Stres Testini Çalıştır")} (${cellCount} ${t("hücre")})`}
            </button>
            {error && <p className="rw-err">{error}</p>}
            {result && renderHeatmap(result)}
            {history.length > 0 && (
              <details className="rw-details">
                <summary>{t("Önceki stres testleri")}</summary>
                {history.map((h) => (
                  <button
                    key={h.stress_id}
                    type="button"
                    className="rw-linklike"
                    onClick={() => setResult(h)}
                  >
                    {h.scenario_id} · {h.summary.passed}/{h.summary.total} {t("geçti")} ·{" "}
                    {new Date(h.created_at).toLocaleString()}
                  </button>
                ))}
              </details>
            )}
          </>
        )}
      </div>
    </div>
  );
};
