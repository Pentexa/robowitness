"use client";

import React, { useEffect, useState } from "react";
import { DatabaseBackup, KeyRound, ScrollText, ShieldCheck, Timer, Trash2 } from "lucide-react";
import {
  createAdminApiKey,
  createBackup,
  createSchedule,
  deleteSchedule,
  fetchAdminApiKeys,
  fetchAudit,
  fetchMetrics,
  fetchPolicyProfiles,
  fetchRobots,
  fetchSchedules,
  revokeAdminApiKey,
  type AdminApiKey,
  type BatterySchedule,
} from "../lib/api";
import { PolicyProfile, RobotProfile } from "../lib/types";

export const AdminPanel: React.FC = () => {
  const [metrics, setMetrics] = useState<Record<string, unknown> | null>(null);
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([]);
  const [keys, setKeys] = useState<AdminApiKey[]>([]);
  const [schedules, setSchedules] = useState<BatterySchedule[]>([]);
  const [robots, setRobots] = useState<RobotProfile[]>([]);
  const [profiles, setProfiles] = useState<PolicyProfile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [newKeyLabel, setNewKeyLabel] = useState("");
  const [newKeyRole, setNewKeyRole] = useState("admin");
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [schedName, setSchedName] = useState("");
  const [schedRobot, setSchedRobot] = useState("");
  const [schedProfile, setSchedProfile] = useState("profile-baseline");
  const [schedInterval, setSchedInterval] = useState("60");

  const refresh = async () => {
    setMetrics(await fetchMetrics().catch(() => null));
    setAudit(await fetchAudit(30).catch(() => []));
    setKeys(await fetchAdminApiKeys().catch(() => []));
    setSchedules(await fetchSchedules().catch(() => []));
    const robotList = await fetchRobots().catch(() => []);
    setRobots(robotList);
    const first = robotList.find((r) => r.simulation_compatible);
    if (first && !schedRobot) setSchedRobot(first.robot_id);
    setProfiles(await fetchPolicyProfiles().catch(() => []));
  };

  useEffect(() => {
    refresh().catch(() => setError("Yönetim verileri yüklenemedi."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
      <section className="rw-section">
        <h3 className="rw-section-title">
          <ShieldCheck size={14} /> Sistem Durumu
        </h3>
        {metrics ? (
          <p className="rw-summary mono">
            alan: {String(metrics.workspace_id)} · karneler: {String(metrics.batteries)} · loglar:{" "}
            {String(metrics.telemetry_imports)} (geçen {String(metrics.telemetry_imports_pass)}) ·
            koşular: {String(metrics.runs_total)} · doğrulamalar: {String(metrics.verifications_total)}
          </p>
        ) : (
          <p className="rw-summary">Metrikler yüklenemedi.</p>
        )}
        <div className="rw-btn-row">
          <button
            id="btn-admin-backup"
            className="rw-btn rw-btn-ghost rw-btn-sm"
            onClick={async () => {
              try {
                const b = await createBackup();
                setNotice(`Yedek alındı: ${b.file} (${b.bytes} bayt, sha256 ${b.sha256.slice(0, 12)}…)`);
              } catch {
                setError("Yedek alınamadı (admin gerekli).");
              }
            }}
          >
            <DatabaseBackup size={14} /> Veritabanı Yedeği Al
          </button>
          <button className="rw-btn rw-btn-ghost rw-btn-sm" onClick={() => refresh()}>
            Yenile
          </button>
        </div>
      </section>

      <section className="rw-section">
        <h3 className="rw-section-title">
          <KeyRound size={14} /> API Anahtarları
        </h3>
        <p className="rw-summary">
          Anahtarlar veritabanında yalnızca özet (hash) olarak saklanır. Yeni anahtar bir kez gösterilir.
          İlk anahtarı oluşturduğunuz anda kimlik doğrulama zorunlu olur — anahtarı kaybetmeyin.
        </p>
        <div className="rw-btn-row">
          <input
            className="rw-input"
            style={{ flex: 1 }}
            placeholder="Etiket (örn. ci-sunucusu)"
            value={newKeyLabel}
            onChange={(e) => setNewKeyLabel(e.target.value)}
          />
          <select className="rw-input" style={{ width: 110 }} value={newKeyRole} onChange={(e) => setNewKeyRole(e.target.value)}>
            <option value="viewer">viewer</option>
            <option value="editor">editor</option>
            <option value="admin">admin</option>
          </select>
          <button
            id="btn-create-api-key"
            className="rw-btn rw-btn-primary rw-btn-sm"
            disabled={!newKeyLabel.trim()}
            onClick={async () => {
              try {
                const ws = (metrics?.workspace_id as string) || "default";
                const created = await createAdminApiKey(newKeyLabel.trim(), newKeyRole, ws);
                setCreatedKey(created.api_key);
                setNewKeyLabel("");
                await refresh();
              } catch {
                setError("Anahtar oluşturulamadı (admin gerekli).");
              }
            }}
          >
            Anahtar Üret
          </button>
        </div>
        {createdKey && (
          <p className="rw-err" role="alert">
            Yeni anahtar (bir kez gösterilir, hemen kopyalayın): <span className="mono">{createdKey}</span>
          </p>
        )}
        {keys.map((k) => (
          <div key={k.key_id} className="rw-table-row" style={{ gridTemplateColumns: "1fr auto auto" }}>
            <span>
              {k.label} <span className="muted text-xs">· {k.role_name} · {k.workspace_id}</span>
            </span>
            <span className="mono text-xs">{k.revoked_at ? "İPTAL" : "AKTİF"}</span>
            {!k.revoked_at && (
              <button
                className="rw-btn rw-btn-ghost rw-btn-sm"
                onClick={async () => {
                  await revokeAdminApiKey(k.key_id).catch(() => setError("Anahtar iptal edilemedi."));
                  await refresh();
                }}
              >
                <Trash2 size={13} /> İptal Et
              </button>
            )}
          </div>
        ))}
      </section>

      <section className="rw-section">
        <h3 className="rw-section-title">
          <Timer size={14} /> Zamanlanmış Bataryalar
        </h3>
        <div className="rw-btn-row">
          <input
            className="rw-input"
            style={{ flex: 1 }}
            placeholder="İsim (örn. Gece sınavı)"
            value={schedName}
            onChange={(e) => setSchedName(e.target.value)}
          />
          <select className="rw-input" style={{ flex: 1 }} value={schedRobot} onChange={(e) => setSchedRobot(e.target.value)}>
            {robots
              .filter((r) => r.simulation_compatible)
              .map((r) => (
                <option key={r.robot_id} value={r.robot_id}>
                  {r.brand} {r.model}
                </option>
              ))}
          </select>
          <select className="rw-input" style={{ flex: 1 }} value={schedProfile} onChange={(e) => setSchedProfile(e.target.value)}>
            {profiles.map((p) => (
              <option key={p.profile_id} value={p.profile_id}>
                {p.name}
              </option>
            ))}
          </select>
          <input
            className="rw-input"
            style={{ width: 90 }}
            type="number"
            min={5}
            value={schedInterval}
            onChange={(e) => setSchedInterval(e.target.value)}
            title="Aralık (dakika)"
          />
          <button
            id="btn-create-schedule"
            className="rw-btn rw-btn-primary rw-btn-sm"
            disabled={!schedName.trim() || !schedRobot}
            onClick={async () => {
              try {
                const profile = profiles.find((p) => p.profile_id === schedProfile);
                if (!profile) return;
                await createSchedule({
                  name: schedName.trim(),
                  robot_id: schedRobot,
                  policy: profile.policy,
                  scenario_ids: [],
                  interval_minutes: Math.max(5, parseInt(schedInterval, 10) || 60),
                });
                setSchedName("");
                await refresh();
                setNotice("Zamanlama oluşturuldu; worker zamanı gelince bataryayı kuyruğa alır.");
              } catch {
                setError("Zamanlama oluşturulamadı.");
              }
            }}
          >
            Ekle
          </button>
        </div>
        {schedules.map((s) => (
          <div key={s.schedule_id} className="rw-table-row" style={{ gridTemplateColumns: "1fr auto auto" }}>
            <span>
              {s.name} <span className="muted text-xs">· {s.robot_id} · {s.interval_minutes} dk</span>
            </span>
            <span className="mono text-xs">sonraki: {new Date(s.next_run_at).toLocaleString("tr-TR")}</span>
            <button
              className="rw-btn rw-btn-ghost rw-btn-sm"
              onClick={async () => {
                await deleteSchedule(s.schedule_id).catch(() => setError("Zamanlama silinemedi."));
                await refresh();
              }}
            >
              <Trash2 size={13} /> Sil
            </button>
          </div>
        ))}
      </section>

      <section className="rw-section">
        <h3 className="rw-section-title">
          <ScrollText size={14} /> Denetim Kaydı (son yazma işlemleri)
        </h3>
        {audit.length === 0 && <p className="rw-summary">Kayıt yok veya admin yetkisi gerekli.</p>}
        {audit.slice(0, 12).map((entry, i) => (
          <p key={i} className="rw-summary mono text-xs">
            {String(entry.created_at).slice(0, 19)} · {String(entry.actor)} · {String(entry.method)}{" "}
            {String(entry.path)} · {String(entry.status_code)}
          </p>
        ))}
      </section>

      {error && <p className="rw-err">{error}</p>}
      {notice && <p className="rw-summary" role="status">{notice}</p>}
    </div>
  );
};
