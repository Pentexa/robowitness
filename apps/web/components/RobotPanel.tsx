"use client";

import React, { useEffect, useState } from "react";
import { Bot, Pencil, Plus, Trash2 } from "lucide-react";
import {
  applyRobotToScenario,
  createRobot,
  deleteRobot,
  fetchRobots,
  updateRobot,
} from "../lib/api";
import { RobotDriveType, RobotProfile, RobotProfileInput, ScenarioSpec } from "../lib/types";

const DRIVE_LABELS: Record<RobotDriveType, string> = {
  differential_drive: "Diferansiyel sürüş (iki tekerlek)",
  ackermann: "Ackermann (otomobil tipi)",
  omnidirectional: "Çok yönlü (mecanum)",
  tracked: "Paletli",
  quadruped: "Dört bacaklı",
  other: "Diğer",
};

const ISSUE_LABELS: Record<string, string> = {
  DRIVE_TYPE_NOT_DIFFERENTIAL_DRIVE: "Simülatör yalnızca diferansiyel sürüşü destekliyor",
  BODY_RADIUS_OUT_OF_SIM_RANGE: "Gövde yarıçapı simülatör aralığı dışında (0,15–0,40 m)",
};

const EMPTY_FORM: RobotProfileInput = {
  brand: "",
  model: "",
  variant: "",
  year: null,
  drive_type: "differential_drive",
  body_radius_m: 0.25,
  wheel_base_m: 0.42,
  wheel_radius_m: 0.09,
  weight_kg: null,
  max_speed_mps: null,
  max_payload_kg: null,
  sensor_type: "2D LiDAR",
  sensor_range_m: 4.0,
  sensor_latency_ms: 0,
  sensor_noise_std_m: 0.0,
  compute_unit: "",
  operating_system: "",
  battery_wh: null,
  notes: "",
};

function toInput(r: RobotProfile): RobotProfileInput {
  const { robot_id: _id, source: _s, created_at: _c, updated_at: _u, simulation_compatible: _sc, compatibility_issues: _ci, ...rest } = r;
  return rest;
}

interface RobotPanelProps {
  scenario: ScenarioSpec | null;
  onScenarioChange: (scenario: ScenarioSpec, robotLabel: string) => void;
}

export const RobotPanel: React.FC<RobotPanelProps> = ({ scenario, onScenarioChange }) => {
  const [robots, setRobots] = useState<RobotProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [form, setForm] = useState<RobotProfileInput>(EMPTY_FORM);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState<boolean>(false);

  const refresh = async (keepSelection = true) => {
    const list = await fetchRobots();
    setRobots(list);
    if (!keepSelection || !list.some((r) => r.robot_id === selectedId)) {
      const firstCompatible = list.find((r) => r.simulation_compatible);
      setSelectedId((firstCompatible ?? list[0])?.robot_id ?? "");
    }
  };

  useEffect(() => {
    refresh(false).catch(() => setError("Robot listesi yüklenemedi. Arka uç açık mı?"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selected = robots.find((r) => r.robot_id === selectedId) ?? null;

  const setNum = (key: keyof RobotProfileInput, raw: string, nullable: boolean) => {
    if (nullable && raw.trim() === "") {
      setForm((f) => ({ ...f, [key]: null }));
      return;
    }
    const value = parseFloat(raw);
    setForm((f) => ({ ...f, [key]: Number.isFinite(value) ? value : f[key] }));
  };

  const handleSave = async () => {
    setError(null);
    setNotice(null);
    if (!form.brand.trim() || !form.model.trim()) {
      setError("Marka ve model zorunludur.");
      return;
    }
    setBusy(true);
    try {
      const payload = { ...form, brand: form.brand.trim(), model: form.model.trim() };
      if (editingId) {
        await updateRobot(editingId, payload);
        setNotice("Robot güncellendi.");
      } else {
        const created = await createRobot(payload);
        setSelectedId(created.robot_id);
        setNotice(`Yeni robot eklendi: ${created.brand} ${created.model}`);
      }
      setForm(EMPTY_FORM);
      setEditingId(null);
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Robot kaydedilemedi");
    } finally {
      setBusy(false);
    }
  };

  const handleDelete = async (robot: RobotProfile) => {
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      await deleteRobot(robot.robot_id);
      setNotice(`Robot silindi: ${robot.brand} ${robot.model}`);
      if (editingId === robot.robot_id) {
        setEditingId(null);
        setForm(EMPTY_FORM);
      }
      await refresh(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Robot silinemedi");
    } finally {
      setBusy(false);
    }
  };

  const handleApply = async () => {
    if (!selected || !scenario) return;
    setError(null);
    setNotice(null);
    setBusy(true);
    try {
      const applied = await applyRobotToScenario(selected.robot_id, scenario);
      onScenarioChange(applied, `${selected.brand} ${selected.model}`);
      setNotice(
        `${selected.brand} ${selected.model} teste uygulandı. Artık “Robotu Çalıştır” bu robotun ölçüleriyle çalışır.`
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Robot teste uygulanamadı");
    } finally {
      setBusy(false);
    }
  };

  const numField = (
    label: string,
    key: keyof RobotProfileInput,
    opts: { step?: string; nullable?: boolean; hint?: string } = {}
  ) => (
    <label className="rw-field">
      <span>{label}</span>
      <input
        className="rw-input"
        type="number"
        step={opts.step ?? "0.01"}
        value={(form[key] as number | null) ?? ""}
        onChange={(e) => setNum(key, e.target.value, opts.nullable ?? false)}
      />
      {opts.hint && <span className="rw-field-hint">{opts.hint}</span>}
    </label>
  );

  const textField = (label: string, key: keyof RobotProfileInput, placeholder = "") => (
    <label className="rw-field">
      <span>{label}</span>
      <input
        className="rw-input"
        type="text"
        placeholder={placeholder}
        value={(form[key] as string) ?? ""}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
      />
    </label>
  );

  return (
    <section className="rw-section">
      <h3 className="rw-section-title">Robot</h3>
      <select
        id="select-robot"
        className="rw-input"
        aria-label="Kayıtlı robotlar"
        value={selectedId}
        onChange={(e) => setSelectedId(e.target.value)}
      >
        {robots.map((r) => (
          <option key={r.robot_id} value={r.robot_id}>
            {r.brand} {r.model}
            {r.variant ? ` (${r.variant})` : ""}
            {r.simulation_compatible ? "" : " — kullanılamaz"}
          </option>
        ))}
      </select>

      {selected && (
        <p className="rw-summary">
          {DRIVE_LABELS[selected.drive_type]} · gövde {selected.body_radius_m} m · {selected.sensor_type}{" "}
          {selected.sensor_range_m} m / {selected.sensor_latency_ms} ms
          {selected.weight_kg !== null ? ` · ${selected.weight_kg} kg` : ""}
          <br />
          {selected.simulation_compatible ? (
            <span className="rw-badge is-live">Testte kullanılabilir</span>
          ) : (
            <span className="rw-badge is-fail">
              Kullanılamaz: {selected.compatibility_issues.map((i) => ISSUE_LABELS[i] ?? i).join("; ")}
            </span>
          )}
        </p>
      )}

      {error && <p className="rw-err">{error}</p>}
      {notice && <p className="rw-summary">{notice}</p>}

      <div className="rw-btn-row">
        <button
          id="btn-apply-robot"
          className="rw-btn rw-btn-primary"
          onClick={handleApply}
          disabled={busy || !selected || !scenario || !selected.simulation_compatible}
          title={selected && !selected.simulation_compatible ? "Bu robot simülatörle uyumlu değil" : undefined}
        >
          <Bot size={15} /> Teste Uygula
        </button>
        {selected?.source === "user" && (
          <>
            <button
              id="btn-edit-robot"
              className="rw-btn rw-btn-ghost rw-btn-sm"
              disabled={busy}
              onClick={() => {
                setForm(toInput(selected));
                setEditingId(selected.robot_id);
              }}
            >
              <Pencil size={14} /> Düzenle
            </button>
            <button
              id="btn-delete-robot"
              className="rw-btn rw-btn-ghost rw-btn-sm"
              disabled={busy}
              onClick={() => handleDelete(selected)}
            >
              <Trash2 size={14} /> Sil
            </button>
          </>
        )}
      </div>

      <details className="rw-details" open={editingId !== null}>
          <summary>{editingId ? "Robotu düzenliyorsunuz" : "Yeni robot ekle"}</summary>
          <div className="rw-form">
            {textField("Marka *", "brand", "örn. ROBOTIS")}
            {textField("Model *", "model", "örn. TurtleBot3 Waffle Pi")}
            {textField("Varyant", "variant", "örn. Lab sürümü")}
            {numField("Üretim yılı", "year", { step: "1", nullable: true })}
            <label className="rw-field">
              <span>Sürüş tipi</span>
              <select
                className="rw-input"
                value={form.drive_type}
                onChange={(e) => setForm((f) => ({ ...f, drive_type: e.target.value as RobotDriveType }))}
              >
                {(Object.keys(DRIVE_LABELS) as RobotDriveType[]).map((d) => (
                  <option key={d} value={d}>
                    {DRIVE_LABELS[d]}
                  </option>
                ))}
              </select>
              <span className="rw-field-hint">Testte yalnızca diferansiyel sürüş kullanılabilir.</span>
            </label>
            {numField("Gövde yarıçapı (m) *", "body_radius_m", { hint: "Test için 0,15–0,40 m arasında olmalı." })}
            {numField("Tekerlek aralığı / dingil mesafesi (m)", "wheel_base_m", { nullable: true })}
            {numField("Tekerlek yarıçapı (m)", "wheel_radius_m", { nullable: true })}
            {numField("Ağırlık (kg)", "weight_kg", { nullable: true })}
            {numField("Azami hız (m/sn)", "max_speed_mps", { nullable: true })}
            {numField("Taşıma kapasitesi (kg)", "max_payload_kg", { nullable: true })}
            {textField("Sensör tipi", "sensor_type", "örn. 2D LiDAR")}
            {numField("Sensör menzili (m)", "sensor_range_m")}
            {numField("Sensör gecikmesi (ms)", "sensor_latency_ms", { step: "1", hint: "0–1000 ms" })}
            {numField("Sensör gürültüsü (m)", "sensor_noise_std_m", { step: "0.01", hint: "0–0,20 m" })}
            {textField("Bilgisayar / işlemci", "compute_unit", "örn. Raspberry Pi 4")}
            {textField("İşletim sistemi", "operating_system", "örn. ROS 2 / Ubuntu 22.04")}
            {numField("Batarya (Wh)", "battery_wh", { nullable: true })}
            <label className="rw-field rw-field-wide">
              <span>Notlar</span>
              <input
                className="rw-input"
                type="text"
                value={form.notes}
                onChange={(e) => setForm((f) => ({ ...f, notes: e.target.value }))}
              />
            </label>
            <div className="rw-actions rw-field-wide">
              <button id="btn-save-robot" className="rw-btn rw-btn-primary" onClick={handleSave} disabled={busy}>
                <Plus size={15} /> {editingId ? "Değişiklikleri Kaydet" : "Yeni Robot Ekle"}
              </button>
              {editingId && (
                <button
                  className="rw-btn rw-btn-ghost"
                  disabled={busy}
                  onClick={() => {
                    setEditingId(null);
                    setForm(EMPTY_FORM);
                  }}
                >
                  Vazgeç
                </button>
              )}
            </div>
          </div>
        </details>
    </section>
  );
};
