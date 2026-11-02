"use client";

import React from "react";
import { FlaskConical } from "lucide-react";
import { useLocale } from "../lib/i18n";
import { PolicyConfig } from "../lib/types";

interface FixComparisonProps {
  baselinePolicy: PolicyConfig;
  candidatePolicy: PolicyConfig;
  onUpdateCandidate: (updated: PolicyConfig) => void;
  onVerify: () => void;
  isVerifying: boolean;
  hasBaseline: boolean;
  provenance: string;
}

const FIELDS: Array<{
  key: "max_speed_mps" | "safe_distance_m" | "reaction_margin_m" | "brake_gain" | "obstacle_prediction_horizon_s";
  label: string;
  unit: string;
  help: string;
  min: number;
  max: number;
  step: number;
}> = [
  {
    key: "max_speed_mps",
    label: "Robot hızı",
    unit: "m/sn",
    help: "Düşürürseniz robot yavaşlar: çarpmaya karşı daha güvenli olur ama süre dolabilir.",
    min: 0.05, max: 1.2, step: 0.05,
  },
  {
    key: "safe_distance_m",
    label: "Engelden uzak durma mesafesi",
    unit: "m",
    help: "Büyütürseniz robot engellerden daha uzaktan geçer.",
    min: 0.2, max: 2.0, step: 0.05,
  },
  {
    key: "reaction_margin_m",
    label: "Erken tepki payı",
    unit: "m",
    help: "Büyütürseniz robot engele daha erken tepki vermeye başlar.",
    min: 0.0, max: 1.0, step: 0.05,
  },
  {
    key: "brake_gain",
    label: "Fren sertliği",
    unit: "×",
    help: "Büyütürseniz robot engele yaklaşınca daha hızlı yavaşlar.",
    min: 0.1, max: 10.0, step: 0.1,
  },
  {
    key: "obstacle_prediction_horizon_s",
    label: "Engeli önceden tahmin süresi",
    unit: "sn",
    help: "Büyütürseniz robot, engelin nereye gideceğini daha uzak gelecekten hesaba katar.",
    min: 0.0, max: 2.0, step: 0.1,
  },
];

export const FixComparison: React.FC<FixComparisonProps> = ({
  baselinePolicy,
  candidatePolicy,
  onUpdateCandidate,
  onVerify,
  isVerifying,
  hasBaseline,
  provenance,
}) => {
  const { t } = useLocale();
  const handleChange = (field: keyof PolicyConfig, value: number) => {
    if (!Number.isFinite(value)) return;
    onUpdateCandidate({ ...candidatePolicy, [field]: value });
  };

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">{t("Düzeltmeyi Dene")}</h3>
          <p className="rw-card-sub">{t("“Eski” değerler ilk çalıştırmadaki ayarlardır. Kaydırıcılarla “Yeni” değerleri değiştirin.")}</p>
        </div>
      </div>
      <div className="rw-card-body">
        {!hasBaseline && (
          <p className="rw-empty">{t("Önce")} <strong>{t("Test")}</strong> {t("sekmesinden robotu eski ayarlarla bir kez çalıştırın. Sonra burada yeni ayarları deneyebilirsiniz.")}</p>
        )}
        {FIELDS.map((f) => {
          const base = baselinePolicy[f.key] as number;
          const cand = candidatePolicy[f.key] as number;
          const changed = base !== cand;
          return (
            <div className="rw-param" key={f.key}>
              <div className="rw-param-top">
                <span className="rw-param-name">
                  {t(f.label)} <span className="muted text-xs">({f.unit})</span>
                </span>
                {changed && <span className="rw-changed">{t("DEĞİŞTİ")}</span>}
              </div>
              <p className="rw-hint">{t(f.help)}</p>
              <div className="rw-param-vals">
                <span className="rw-param-old">{t("Eski:")} {Number(base).toFixed(2)}</span>
                <input
                  id={`slider-${f.key.replace(/_/g, "-")}`}
                  type="range"
                  step={f.step}
                  min={f.min}
                  max={f.max}
                  value={cand}
                  onChange={(e) => handleChange(f.key, parseFloat(e.target.value))}
                  aria-label={`${f.label} kaydırıcı`}
                />
                <input
                  id={`input-${f.key.replace(/_/g, "-")}`}
                  type="number"
                  step={f.step}
                  min={f.min}
                  max={f.max}
                  value={cand}
                  onChange={(e) => handleChange(f.key, parseFloat(e.target.value))}
                  className="rw-input"
                  aria-label={`Yeni ${f.label}`}
                />
              </div>
            </div>
          );
        })}
        <button
          id="btn-verify-fix"
          className="rw-btn rw-btn-primary rw-btn-big"
          onClick={onVerify}
          disabled={isVerifying || !hasBaseline}
          title={hasBaseline ? undefined : t("Önce robotu bir kez çalıştırın")}
        >
          <FlaskConical size={16} />
          {isVerifying ? t("Testler çalışıyor, bekleyin…") : t("Düzeltmeyi Test Et")}
        </button>
        <p className="rw-hint">
          {t("Bu buton yeni ayarları aynı testte, ayrıca robotun görmediği 20 yeni testte ve önemli eski testlerde dener. Biraz sürebilir; pencereyi kapatmayın. Geçen çözüm, Meta AI'ın başarısı olarak mühürlü karara dönüşür.")}
        </p>
        <details className="rw-details">
          <summary>{t("Teknik detaylar (isteğe bağlı)")}</summary>
          <div>
            <span className="mono text-xs">{t("Kaynak:")} {provenance}</span>
            <span className="mono text-xs">{t("Eski ayar kodu:")} {baselinePolicy.id} · {t("Yeni ayar kodu:")} {candidatePolicy.id}</span>
          </div>
        </details>
      </div>
    </div>
  );
};
