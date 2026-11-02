"use client";

import React, { useState } from "react";
import { SearchCheck } from "lucide-react";
import { InvestigationResponse, PolicyPatch, RunResult } from "../lib/types";
import { RunVerdict } from "./RunVerdict";

interface FailureAnalysisProps {
  runId: string | null;
  runResult: RunResult | null;
  minClearanceLimitM?: number;
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
  runResult,
  minClearanceLimitM,
  investigation,
  onInvestigate,
  onApplyPatch,
}) => {
  const oracleStatus = runResult?.oracle_status ?? null;
  const runFailed = runResult ? runResult.oracle_status === "FAIL" : null;
  const nearMiss =
    runResult !== null &&
    runResult.oracle_status === "FAIL" &&
    !runResult.metrics.collision_detected &&
    runResult.metrics.goal_reached;
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
          <h3 className="rw-card-title">İnceleme</h3>
          <p className="rw-card-sub">
            {nearMiss
              ? "Çarpışma olmadı ama robot engele çok yakın geçti. Bu yakın geçiş neden oldu?"
              : "Robot neden çarptı ya da neden hedefe ulaşamadı?"}
          </p>
        </div>
        {investigation && (
          <span className="rw-badge mono">
            {investigation.provenance === "LIVE_META" ? "Meta AI · Canlı" : "Çevrimdışı Yedek"}
          </span>
        )}
      </div>
      <div className="rw-card-body">
        {runResult && <RunVerdict result={runResult} minClearanceLimitM={minClearanceLimitM} />}
        {!runId && (
          <p className="rw-empty">
            Önce <strong>Test</strong> sekmesinden robotu bir kez çalıştırın. Robot başarısız olursa nedeni burada
            incelenecek.
          </p>
        )}
        {runId && runFailed === false && !investigation && (
          <p className="rw-empty">
            {oracleStatus === "PASS" ? (
              <>
                Bu çalıştırma <strong>kazasız tamamlandı</strong> (bağımsız kontrol: GEÇTİ). İncelenecek bir
                hata yok. İsterseniz Test sekmesinden başka bir senaryo veya robot seçip tekrar çalıştırın.
              </>
            ) : (
              <>
                Bu çalıştırmada bağımsız kontrol kesin karar veremedi (BELİRSİZ). İncelenecek kesin bir hata
                yok; tekrar çalıştırmayı veya başka senaryo denemeyi seçin.
              </>
            )}
          </p>
        )}
        {runId && runFailed !== false && !investigation && (
          <>
            <p className="rw-intro">
              {nearMiss
                ? "Çarpışma olmadı; ancak yukarıda yazdığı gibi robot güvenli mesafeyi koruyamadı. Meta AI ölçümlere bakıp bu yakın geçişin nedenini açıklasın ve bir düzeltme önersin."
                : "Çalıştırma bitti. Şimdi Meta AI, kaydedilen ölçümlere bakarak hatanın nedenini açıklasın ve çözümünü önersin. Meta AI'ın çözümü bağımsız sınavda ölçülerek kanıtlanır; geçen çözüm mühürlü karara dönüşür."}
            </p>
            <button id="btn-investigate" className="rw-btn rw-btn-primary rw-btn-block" onClick={handleInvestigate} disabled={isLoading}>
              <SearchCheck size={16} />
              {isLoading ? "İnceleniyor…" : nearMiss ? "Yakın Geçişi İncele" : "Hatayı İncele"}
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
                <span className="rw-spec-label">Meta AI'ın rolü</span>
                <span className="rw-spec-value">Çözümü üretir · sınavda kanıtlanır</span>
              </div>
            </div>
            <div>
              <div className="rw-spec-label">Meta AI'ın açıklaması</div>
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
