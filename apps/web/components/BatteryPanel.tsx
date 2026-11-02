"use client";

import React, { useEffect, useState } from "react";
import { ClipboardList, Download, Upload } from "lucide-react";
import {
  compareBatteries,
  createBattery,
  downloadBatteryReport,
  fetchBatteries,
  fetchBattery,
  fetchBatteryTrend,
  runFleet,
  type BatteryTrendPoint,
  fetchJob,
  fetchLocalPolicies,
  fetchPolicyProfiles,
  fetchRobots,
  importTelemetry,
} from "../lib/api";
import { REASON_LABELS } from "./RunVerdict";
import type { BatteryCompareEntry } from "../lib/api";
import {
  BatteryResult,
  ImportResult,
  LocalPolicyInfo,
  PolicyProfile,
  RobotProfile,
} from "../lib/types";

const STATUS_TR: Record<string, string> = {
  PASS: "GEÇTİ",
  FAIL: "KALDI",
  INCONCLUSIVE: "BELİRSİZ",
};

interface BatteryPanelProps {
  onLoadRun: (runId: string) => void;
}

export const BatteryPanel: React.FC<BatteryPanelProps> = ({ onLoadRun }) => {
  const [robots, setRobots] = useState<RobotProfile[]>([]);
  const [profiles, setProfiles] = useState<PolicyProfile[]>([]);
  const [robotId, setRobotId] = useState<string>("");
  const [profileId, setProfileId] = useState<string>("profile-baseline");
  const [localInfo, setLocalInfo] = useState<LocalPolicyInfo | null>(null);
  const [localPolicy, setLocalPolicy] = useState<string>("");
  const [battery, setBattery] = useState<BatteryResult | null>(null);
  const [history, setHistory] = useState<BatteryResult[]>([]);
  const [progress, setProgress] = useState<string | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [trend, setTrend] = useState<BatteryTrendPoint[]>([]);
  const [fleetSelected, setFleetSelected] = useState<string[]>([]);
  const [fleetCards, setFleetCards] = useState<BatteryResult[]>([]);
  const [fleetSkipped, setFleetSkipped] = useState<Array<{ robot_id: string; reason: string }>>([]);
  const [fleetRunning, setFleetRunning] = useState<boolean>(false);

  const [compareA, setCompareA] = useState<string>("");
  const [compareB, setCompareB] = useState<string>("");
  const [compareEntries, setCompareEntries] = useState<BatteryCompareEntry[] | null>(null);
  const [compareError, setCompareError] = useState<string | null>(null);

  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [goalX, setGoalX] = useState<string>("");
  const [goalY, setGoalY] = useState<string>("");

  useEffect(() => {
    fetchRobots()
      .then((list) => {
        setRobots(list);
        const first = list.find((r) => r.simulation_compatible);
        if (first) setRobotId(first.robot_id);
      })
      .catch(() => setError("Robot listesi yüklenemedi."));
    fetchPolicyProfiles()
      .then(setProfiles)
      .catch(() => setError("Profiller yüklenemedi."));
    fetchLocalPolicies()
      .then(setLocalInfo)
      .catch(() => console.warn("Local policies unavailable"));
    fetchBatteries(5)
      .then(setHistory)
      .catch(() => console.warn("Battery history unavailable"));
    fetchBatteryTrend()
      .then(setTrend)
      .catch(() => console.warn("Battery trend unavailable"));
  }, []);

  const refreshTrend = async () => {
    setTrend(await fetchBatteryTrend().catch(() => []));
    setHistory(await fetchBatteries(5).catch(() => []));
  };

  const handleRunFleet = async () => {
    const profile = profiles.find((p) => p.profile_id === profileId);
    if (!profile || fleetSelected.length === 0) return;
    setFleetRunning(true);
    setFleetCards([]);
    setFleetSkipped([]);
    try {
      const result = await runFleet(fleetSelected, profile.policy);
      setFleetSkipped(result.skipped);
      const pending = new Map(result.jobs.map((j) => [j.job_id, j.battery_id]));
      const done = new Map<string, BatteryResult>();
      const timer = setInterval(async () => {
        try {
          for (const [jobId, batteryId] of Array.from(pending.entries())) {
            const jobState = await fetchJob(jobId);
            if (jobState.status === "completed") {
              done.set(batteryId, await fetchBattery(batteryId));
              pending.delete(jobId);
            } else if (jobState.status === "failed" || jobState.status === "cancelled") {
              pending.delete(jobId);
            }
          }
          if (pending.size === 0) {
            clearInterval(timer);
            setFleetCards(
              Array.from(done.values()).sort((x, y) => y.summary.passed - x.summary.passed)
            );
            setFleetRunning(false);
            await refreshTrend().catch(() => undefined);
          }
        } catch {
          clearInterval(timer);
          setFleetRunning(false);
        }
      }, 1500);
    } catch {
      setFleetRunning(false);
      setError("Filo bataryası başlatılamadı.");
    }
  };

  const handleRunBattery = async () => {
    const profile = profiles.find((p) => p.profile_id === profileId);
    if (!robotId || !profile) return;
    setRunning(true);
    setError(null);
    setBattery(null);
    setProgress("Batarya başlatılıyor…");
    try {
      const job = await createBattery(robotId, profile.policy, undefined, localPolicy || null);
      const timer = setInterval(async () => {
        try {
          const jobState = await fetchJob(job.job_id);
          if (jobState.progress) {
            setProgress(
              `Çalışıyor: ${jobState.progress.current_step}/${jobState.progress.total_steps} — ${jobState.progress.message}`
            );
          }
          if (jobState.status === "completed") {
            clearInterval(timer);
            const card = await fetchBattery(job.result_id);
            setBattery(card);
            setHistory(await fetchBatteries(5).catch(() => []));
            setTrend(await fetchBatteryTrend().catch(() => []));
            setProgress(null);
            setRunning(false);
          } else if (jobState.status === "failed" || jobState.status === "cancelled") {
            clearInterval(timer);
            setProgress(null);
            setRunning(false);
            setError("Batarya çalışması başarısız oldu.");
          }
        } catch {
          clearInterval(timer);
          setRunning(false);
          setProgress(null);
          setError("Batarya durumu okunamadı.");
        }
      }, 1000);
    } catch (e) {
      setRunning(false);
      setProgress(null);
      setError(e instanceof Error ? e.message : "Batarya başlatılamadı");
    }
  };

  const handleImportFile = async (file: File) => {
    setImportError(null);
    setImportResult(null);
    try {
      const content = await file.text();
      const format = file.name.toLowerCase().endsWith(".csv") ? "csv" : "json";
      const gx = parseFloat(goalX);
      const gy = parseFloat(goalY);
      const result = await importTelemetry({
        name: file.name,
        robot_label: "",
        format,
        content,
        goal: Number.isFinite(gx) && Number.isFinite(gy) ? { x_m: gx, y_m: gy } : null,
      });
      setImportResult(result);
    } catch (e) {
      setImportError(e instanceof Error ? e.message : "Dosya yüklenemedi");
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      <section className="rw-section">
        <h3 className="rw-section-title">Robot Sınav Karnesi</h3>
        <p className="rw-summary">
          Seçili robot, hazır senaryoların tamamından (referans + 10 kütüphane senaryosu) tek tek geçer.
          Sonuçlar ölçülür; bu karne simülasyon karnedir, gerçek dünya onayı değildir.
        </p>
        <label className="rw-field">
          <span>Robot</span>
          <select
            id="select-battery-robot"
            className="rw-input"
            value={robotId}
            onChange={(e) => setRobotId(e.target.value)}
          >
            {robots.map((r) => (
              <option key={r.robot_id} value={r.robot_id} disabled={!r.simulation_compatible}>
                {r.brand} {r.model}
                {r.simulation_compatible ? "" : " — kullanılamaz"}
              </option>
            ))}
          </select>
        </label>
        <label className="rw-field">
          <span>Ayar profili</span>
          <select
            id="select-battery-profile"
            className="rw-input"
            value={profileId}
            onChange={(e) => setProfileId(e.target.value)}
          >
            {profiles.map((p) => (
              <option key={p.profile_id} value={p.profile_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        {localInfo?.enabled && (
          <label className="rw-field">
            <span>Kendi kodum (yerel politika, isteğe bağlı)</span>
            <select
              id="select-battery-local-policy"
              className="rw-input"
              value={localPolicy}
              onChange={(e) => setLocalPolicy(e.target.value)}
            >
              <option value="">— Kullanma (profil ayarları) —</option>
              {localInfo.policies.map((p) => (
                <option key={p.name} value={p.name}>
                  {p.name}.py
                </option>
              ))}
            </select>
          </label>
        )}
        <button
          id="btn-run-battery"
          className="rw-btn rw-btn-primary rw-btn-big"
          onClick={handleRunBattery}
          disabled={running || !robotId}
        >
          <ClipboardList size={16} />
          {running ? "Batarya çalışıyor…" : "Bataryayı Çalıştır (tüm senaryolar)"}
        </button>
        {progress && <p className="rw-summary mono">{progress}</p>}
        {error && <p className="rw-err">{error}</p>}
      </section>

      {battery && (
        <section className="rw-section">
          <h3 className="rw-section-title">
            Karne — {battery.robot_label} ({battery.policy_id})
          </h3>
          <p className="rw-summary">
            <strong>{battery.summary.passed}/{battery.summary.total} geçti</strong> · Çarpışma:{" "}
            {battery.summary.collisions} · Yakın geçiş: {battery.summary.near_misses} · En kötü mesafe:{" "}
            {battery.summary.worst_clearance_m} m
          </p>
          <div>
            {battery.entries.map((e) => (
              <div key={e.run_id} className="rw-table-row" style={{ gridTemplateColumns: "1fr auto auto" }}>
                <span>
                  {e.title}
                  <span className="muted text-xs">
                    {" "}
                    · {e.metrics.min_clearance_m} m
                    {e.near_miss ? " · yakın geçiş" : ""}
                    {e.reason_codes.length > 0
                      ? ` · ${e.reason_codes.map((c) => REASON_LABELS[c] ?? c).join(", ")}`
                      : ""}
                  </span>
                </span>
                <span className={`rw-badge ${e.oracle_status === "PASS" ? "is-solid" : e.oracle_status === "FAIL" ? "is-fail" : ""}`}>
                  {STATUS_TR[e.oracle_status]}
                </span>
                <button className="rw-btn rw-btn-ghost rw-btn-sm" onClick={() => onLoadRun(e.run_id)}>
                  Tekrarı İzle
                </button>
              </div>
            ))}
          </div>
          <button
            id="btn-download-report"
            className="rw-btn rw-btn-ghost"
            onClick={() => downloadBatteryReport(battery.battery_id).catch(() => setError("Karne indirilemedi"))}
          >
            <Download size={15} /> Karneyi İndir (.md)
          </button>
        </section>
      )}

      {history.length >= 2 && (
        <section className="rw-section">
          <h3 className="rw-section-title">Karne Karşılaştırma (A → B)</h3>
          <div className="rw-btn-row">
            <select
              id="select-compare-a"
              className="rw-input"
              style={{ flex: 1 }}
              value={compareA}
              onChange={(e) => setCompareA(e.target.value)}
              aria-label="Karşılaştırma A karnesi"
            >
              <option value="">A: eski karne</option>
              {history.map((h) => (
                <option key={h.battery_id} value={h.battery_id}>
                  {h.robot_label} · {h.summary.passed}/{h.summary.total} · {new Date(h.created_at).toLocaleString("tr-TR")}
                </option>
              ))}
            </select>
            <select
              id="select-compare-b"
              className="rw-input"
              style={{ flex: 1 }}
              value={compareB}
              onChange={(e) => setCompareB(e.target.value)}
              aria-label="Karşılaştırma B karnesi"
            >
              <option value="">B: yeni karne</option>
              {history.map((h) => (
                <option key={h.battery_id} value={h.battery_id}>
                  {h.robot_label} · {h.summary.passed}/{h.summary.total} · {new Date(h.created_at).toLocaleString("tr-TR")}
                </option>
              ))}
            </select>
            <button
              id="btn-compare-batteries"
              className="rw-btn rw-btn-primary rw-btn-sm"
              disabled={!compareA || !compareB || compareA === compareB}
              onClick={async () => {
                setCompareError(null);
                try {
                  const result = await compareBatteries(compareA, compareB);
                  setCompareEntries(result.entries);
                } catch {
                  setCompareError("Karşılaştırma yapılamadı.");
                }
              }}
            >
              Karşılaştır
            </button>
          </div>
          {compareError && <p className="rw-err">{compareError}</p>}
          {compareEntries && (
            <div>
              {compareEntries.map((e) => (
                <div key={e.scenario_id} className="rw-table-row" style={{ gridTemplateColumns: "1fr auto auto" }}>
                  <span>
                    {e.title}
                    <span className="muted text-xs">
                      {" "}· {e.clearance_a ?? "—"} → {e.clearance_b ?? "—"} m
                    </span>
                  </span>
                  <span className="mono text-xs">
                    {e.status_a ?? "—"} → {e.status_b ?? "—"}
                  </span>
                  <span
                    className={`rw-badge ${e.outcome === "improved" ? "is-solid" : e.outcome === "worsened" ? "is-fail" : ""}`}
                  >
                    {e.outcome === "improved"
                      ? "İYİLEŞTİ"
                      : e.outcome === "worsened"
                        ? "KÖTÜLEŞTİ"
                        : e.outcome === "same"
                          ? "AYNI"
                          : e.outcome.toUpperCase()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>
      )}

      {history.length > 0 && (
        <section className="rw-section">
          <h3 className="rw-section-title">Geçmiş Karneler</h3>
          <select
            id="select-battery-history"
            className="rw-input"
            aria-label="Geçmiş karneler"
            value={battery?.battery_id ?? ""}
            onChange={(e) => {
              const found = history.find((h) => h.battery_id === e.target.value);
              if (found) setBattery(found);
            }}
          >
            <option value="">— Karne seçin —</option>
            {history.map((h) => (
              <option key={h.battery_id} value={h.battery_id}>
                {h.robot_label} · {h.summary.passed}/{h.summary.total} geçti ·{" "}
                {new Date(h.created_at).toLocaleString("tr-TR")}
              </option>
            ))}
          </select>
        </section>
      )}

      {trend.length > 0 && (
        <section className="rw-section">
          <h3 className="rw-section-title">Karne Trendi (geçme oranı)</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {trend.slice(-10).map((p) => (
              <div key={p.battery_id} className="rw-btn-row" style={{ alignItems: "center" }}>
                <span className="text-xs muted" style={{ width: 130, flex: "none" }}>
                  {new Date(p.created_at).toLocaleDateString("tr-TR")}
                </span>
                <span className="text-xs" style={{ flex: 1 }}>
                  {p.robot_label}
                </span>
                <span
                  aria-hidden="true"
                  style={{
                    width: `${Math.round(p.pass_rate * 120)}px`,
                    height: 10,
                    background: "#111",
                    display: "inline-block",
                  }}
                />
                <span className="mono text-xs">
                  {p.passed}/{p.total} (%{Math.round(p.pass_rate * 100)})
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="rw-section">
        <h3 className="rw-section-title">Filo Bataryası (birden çok robot)</h3>
        <p className="rw-summary">
          Aynı ayar profiliyle birden çok robotu aynı bataryadan geçirip sıralayın. Uyumsuz robotlar
          nedenleriyle atlanır.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {robots
            .filter((r) => r.simulation_compatible)
            .map((r) => (
              <label key={r.robot_id} className="rw-btn-row" style={{ alignItems: "center" }}>
                <input
                  type="checkbox"
                  checked={fleetSelected.includes(r.robot_id)}
                  onChange={(e) =>
                    setFleetSelected((prev) =>
                      e.target.checked
                        ? [...prev, r.robot_id]
                        : prev.filter((x) => x !== r.robot_id)
                    )
                  }
                />
                <span>
                  {r.brand} {r.model}
                </span>
              </label>
            ))}
        </div>
        <button
          id="btn-run-fleet"
          className="rw-btn rw-btn-primary"
          onClick={handleRunFleet}
          disabled={fleetRunning || fleetSelected.length === 0}
        >
          {fleetRunning ? "Filo çalışıyor…" : `Filo Bataryasını Çalıştır (${fleetSelected.length} robot)`}
        </button>
        {fleetSkipped.length > 0 && (
          <p className="rw-summary">
            Atlananlar: {fleetSkipped.map((s) => `${s.robot_id} (${s.reason})`).join("; ")}
          </p>
        )}
        {fleetCards.length > 0 && (
          <div>
            {fleetCards.map((card, i) => (
              <div key={card.battery_id} className="rw-table-row" style={{ gridTemplateColumns: "auto 1fr auto" }}>
                <span className="mono">{i + 1}.</span>
                <span>{card.robot_label}</span>
                <span className="mono text-xs">
                  {card.summary.passed}/{card.summary.total} geçti · çarpışma {card.summary.collisions} ·
                  yakın {card.summary.near_misses}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rw-section">
        <h3 className="rw-section-title">Gerçek Sürüş Yükle (Log)</h3>
        <p className="rw-summary">
          Gerçek robotun kaydettiği sürüş dosyasını yükleyin; aynı kurallarla (çarpışma, güvenli mesafe,
          hedef) değerlendirilir. Bu ölçüm simülasyon değildir — etiketi: GERÇEK_LOG.
        </p>
        <div className="rw-btn-row">
          <input
            className="rw-input"
            placeholder="Hedef x (isteğe bağlı)"
            value={goalX}
            onChange={(e) => setGoalX(e.target.value)}
          />
          <input
            className="rw-input"
            placeholder="Hedef y (isteğe bağlı)"
            value={goalY}
            onChange={(e) => setGoalY(e.target.value)}
          />
        </div>
        <label className="rw-btn rw-btn-ghost" style={{ cursor: "pointer" }}>
          <Upload size={15} /> CSV / JSON Dosyası Seç
          <input
            id="input-import-telemetry"
            type="file"
            accept=".csv,.json,.jsonl"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleImportFile(f).catch(() => setImportError("Dosya okunamadı"));
            }}
          />
        </label>
        <p className="rw-summary">
          CSV başlıkları: <span className="mono">t_s,x_m,y_m,yaw_rad,min_obstacle_distance_m</span>
        </p>
        {importError && <p className="rw-err">{importError}</p>}
        {importResult && (
          <div className={`rw-verdict ${importResult.oracle_status === "PASS" ? "is-solid" : importResult.oracle_status === "FAIL" ? "is-fail" : ""}`} role="status">
            <span className="rw-verdict-label">Gerçek sürüş sonucu — GERÇEK_LOG ({importResult.name})</span>
            <span className="rw-verdict-value">
              {importResult.oracle_status === "PASS"
                ? "KAZASIZ ✓"
                : importResult.near_miss
                  ? "HEDEFE ULAŞTI AMA GÜVENLİ DEĞİL ✗"
                  : importResult.oracle_status === "FAIL"
                    ? "BAŞARISIZ ✗"
                    : "KARAR VERİLEMEDİ"}
            </span>
            <span className="rw-verdict-sub">
              {importResult.reason_codes.map((c) => REASON_LABELS[c] ?? c).join(" · ") || "Kural ihlali yok"} ·
              En yakın mesafe {importResult.metrics.min_clearance_m ?? "—"} m · Süre{" "}
              {importResult.metrics.duration_s} sn · Yol {importResult.metrics.path_length_m} m
            </span>
          </div>
        )}
      </section>
    </div>
  );
};
