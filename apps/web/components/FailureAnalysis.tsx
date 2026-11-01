"use client";

import React, { useState } from "react";
import { SearchCheck } from "lucide-react";
import { InvestigationResponse, PolicyPatch } from "../lib/types";

interface FailureAnalysisProps {
  runId: string | null;
  investigation: InvestigationResponse | null;
  onInvestigate: () => Promise<void>;
  onApplyPatch: (patch: PolicyPatch) => void;
}

const PATCH_LABELS: Array<{ key: keyof PolicyPatch; label: string; unit: string }> = [
  { key: "max_speed_mps", label: "Robot hızı", unit: "m/sn" },
  { key: "safe_distance_m", label: "Engelden uzak durma", unit: "m" },
  { key: "reaction_margin_m", label: "Erken tepki payı", unit: "m" },
  { key: "brake_gain", label: "Fren sertliği", unit: "×" },
  { key: "obstacle_prediction_horizon_s", label: "Engeli önceden tahmin", unit: "sn" },
];

export const FailureAnalysis: React.FC<FailureAnalysisProps> = ({
  runId,
  investigation,
  onInvestigate,
  onApplyPatch,
}) => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleInvestigate = async () => {
    if (!runId) return;
    setIsLoading(true);
    setError(null);
    try {
      await onInvestigate();
    } catch (e) {
      setError(e instanceof Error ? e.message : "İnceleme isteği başarısız oldu");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">Hata İnceleme</h3>
          <p className="rw-card-sub">Robot neden çarptı ya da neden hedefe ulaşamadı?</p>
        </div>
        {investigation && <span className="rw-badge mono">{investigation.provenance === "LIVE_META" ? "YAPAY ZEKÂ" : "ÇEVRİMDIŞI"}</span>}
      </div>
      <div className="rw-card-body">
        {!runId && (
          <p className="rw-empty">
            Önce <strong>Test</strong> sekmesinden robotu bir kez çalıştırın. Robot başarısız olursa nedeni burada
            incelenecek.
          </p>
        )}
        {runId && !investigation && (
          <>
            <p className="rw-intro">
              Çalıştırma bitti. Şimdi yapay zekâ, kaydedilen ölçümlere bakarak hatanın muhtemel nedenini açıklasın
              ve bir düzeltme önersin.
            </p>
            <button id="btn-investigate" className="rw-btn rw-btn-primary rw-btn-block" onClick={handleInvestigate} disabled={isLoading}>
              <SearchCheck size={16} />
              {isLoading ? "İnceleniyor…" : "Hatayı İncele"}
            </button>
          </>
        )}
        {error && <p className="rw-err">İnceleme yapılamadı: {error}</p>}
        {investigation && (
          <>
            <div className="rw-spec">
              <div className="rw-spec-item">
                <span className="rw-spec-label">Sorunun olduğu an</span>
                <span className="rw-spec-value mono">{investigation.failure_tick}. adım</span>
              </div>
              <div className="rw-spec-item">
                <span className="rw-spec-label">Karar verir mi?</span>
                <span className="rw-spec-value">Hayır, sadece önerir</span>
              </div>
            </div>
            <div>
              <div className="rw-spec-label">Yapay zekânın açıklaması</div>
              <p className="text-sm">{investigation.hypothesis}</p>
            </div>
            <div>
              <div className="rw-spec-label">Ölçümlerde ne görüldü?</div>
              <p className="text-sm muted">{investigation.evidence_summary}</p>
            </div>
            <div>
              <div className="rw-spec-label">Önerilen yeni ayarlar</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 6 }}>
                {PATCH_LABELS.filter((f) => investigation.suggested_patch[f.key] !== undefined).map((f) => (
                  <div key={f.key} className="rw-between" style={{ fontSize: "0.84rem" }}>
                    <span>{f.label}</span>
                    <span className="mono">
                      {investigation.suggested_patch[f.key]} {f.unit}
                    </span>
                  </div>
                ))}
                {PATCH_LABELS.every((f) => investigation.suggested_patch[f.key] === undefined) && (
                  <span className="muted text-sm">Öneride sayısal bir değişiklik yok.</span>
                )}
              </div>
            </div>
            <button id="btn-apply-patch" className="rw-btn rw-btn-primary rw-btn-block" onClick={() => onApplyPatch(investigation.suggested_patch)}>
              Bu Öneriyi Kullan (Düzeltme sekmesine geç)
            </button>
            <details className="rw-details">
              <summary>Teknik detaylar (isteğe bağlı)</summary>
              <div>
                <span className="mono text-xs">Çalıştırma kodu: {investigation.run_id}</span>
                <span className="mono text-xs">Kaynak: {investigation.provenance}</span>
                <pre className="rw-code">{JSON.stringify(investigation.suggested_patch, null, 2)}</pre>
              </div>
            </details>
          </>
        )}
      </div>
    </div>
  );
};
