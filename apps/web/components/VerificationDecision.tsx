"use client";

import React from "react";
import { Check, Clock, Minus, X } from "lucide-react";
import { VerificationRecord } from "../lib/types";

interface VerificationDecisionProps {
  verification: VerificationRecord | null;
  isVerifying: boolean;
}

const GATE_INFO: Record<string, { title: string; desc: string }> = {
  GATE_1_REPRODUCE: {
    title: "1. Kontrol — Eski hata tekrar oluştu mu?",
    desc: "İlk çalıştırmanın hatası aynı testte tekrar görülmeli. Görülmezse karşılaştırma adil olmaz.",
  },
  GATE_2_PAIRED: {
    title: "2. Kontrol — Yeni ayarlar aynı testte daha iyi mi?",
    desc: "Yeni ayarlar, eski ayarlarla birebir aynı testte yarıştırılır.",
  },
  GATE_3_HOLDOUT: {
    title: "3. Kontrol — Görmediği 20 yeni testten geçti mi?",
    desc: "Robotun daha önce görmediği 20 testin tamamından geçmeli.",
  },
  GATE_4_REGRESSION: {
    title: "4. Kontrol — Eskiden geçen testler bozuldu mu?",
    desc: "Yeni ayarlar, önemli eski testleri bozmamalı.",
  },
  GATE_5_INTEGRITY: {
    title: "5. Kontrol — Sonuç dosyaları tam ve değişmemiş mi?",
    desc: "Rapor dosyalarının eksiksiz ve sonradan değiştirilmemiş olduğu doğrulanır.",
  },
};

const STATUS_TR: Record<string, string> = {
  PASS: "GEÇTİ",
  FAIL: "KALDI",
  RUNNING: "ÇALIŞIYOR",
  NOT_RUN: "HENÜZ YAPILMADI",
  INCONCLUSIVE: "BELİRSİZ",
};

const VERDICT_TR: Record<string, { title: string; sub: string }> = {
  VERIFIED_IN_SIMULATION: {
    title: "DÜZELTME KABUL EDİLDİ",
    sub: "Yeni ayarlar bütün kontrollerden geçti. Bu sonuç yalnızca bu simülasyon (bilgisayar testi) için geçerlidir; gerçek robotta ayrıca denenmelidir.",
  },
  REJECTED: {
    title: "DÜZELTME REDDEDİLDİ",
    sub: "Yeni ayarlar kontrollerden en az birinde kaldı. Ayarları değiştirip “Düzeltmeyi Test Et”e tekrar basabilirsiniz.",
  },
  INCONCLUSIVE: {
    title: "SONUÇ BELİRSİZ",
    sub: "Test tamamlanamadı ya da bir şeyler eksik kaldı. Tekrar denemeden bu ayarlara güvenmeyin.",
  },
};

export const VerificationDecision: React.FC<VerificationDecisionProps> = ({
  verification,
  isVerifying,
}) => {
  if (!verification && !isVerifying) {
    return (
      <div className="rw-card">
        <div className="rw-card-head">
          <div>
            <h3 className="rw-card-title">Sonuç</h3>
            <p className="rw-card-sub">Düzeltme kabul edildi mi, reddedildi mi?</p>
          </div>
        </div>
        <div className="rw-card-body">
          <p className="rw-empty">
            Henüz sonuç yok. Önce <strong>Düzeltme</strong> sekmesinden “Düzeltmeyi Test Et”e basın. Karar burada
            büyük harflerle gösterilecek.
          </p>
        </div>
      </div>
    );
  }

  const verdict = verification?.verdict ?? "INCONCLUSIVE";
  const failed = verdict === "REJECTED";
  const passed = verdict === "VERIFIED_IN_SIMULATION";
  const verdictInfo = VERDICT_TR[verdict] ?? VERDICT_TR.INCONCLUSIVE;

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">Sonuç</h3>
          <p className="rw-card-sub">Meta AI'ın çözümünün bağımsız ölçümle kanıtlanmış sonucu.</p>
        </div>
        <span className={`rw-badge mono ${passed ? "is-solid" : failed ? "is-fail" : ""}`}>
          {isVerifying ? "TEST ÇALIŞIYOR" : verdictInfo.title}
        </span>
      </div>
      <div className="rw-card-body">
        <div className={`rw-verdict ${passed ? "is-solid" : ""} ${failed ? "is-fail" : ""}`}>
          <span className="rw-verdict-label">Nihai karar</span>
          <span className="rw-verdict-value">
            {isVerifying ? "Testler çalışıyor…" : `${passed ? "✓ " : failed ? "✕ " : "— "}${verdictInfo.title}`}
          </span>
          {!isVerifying && <span className="rw-verdict-sub">{verdictInfo.sub}</span>}
        </div>
        <div className="rw-gates">
          {(verification?.gates ?? []).map((g) => {
            const info = GATE_INFO[g.gate_id];
            return (
              <div key={g.gate_id} className={`rw-gate ${g.status === "FAIL" ? "is-fail" : ""} ${g.status === "PASS" ? "is-pass" : ""}`}>
                <span className="rw-gate-icon">
                  {g.status === "PASS" ? (
                    <Check size={13} />
                  ) : g.status === "FAIL" ? (
                    <X size={13} color="#111111" />
                  ) : g.status === "RUNNING" ? (
                    <Clock size={13} color="#555555" />
                  ) : (
                    <Minus size={13} color="#555555" />
                  )}
                </span>
                <div className="rw-gate-body">
                  <div className="rw-gate-top">
                    <span className="rw-gate-name">{info ? info.title : g.name}</span>
                    <span className={`rw-gate-status ${g.status === "FAIL" ? "bad" : ""}`}>{STATUS_TR[g.status] ?? g.status}</span>
                  </div>
                  {info && <span className="rw-gate-desc">{info.desc}</span>}
                  {g.reason_codes.length > 0 && (
                    <details className="rw-details">
                      <summary>Teknik neden kodları</summary>
                      <div>
                        <span className="rw-gate-reasons">{g.reason_codes.join(" · ")}</span>
                      </div>
                    </details>
                  )}
                </div>
              </div>
            );
          })}
        </div>
        {verification && (
          <details className="rw-details">
            <summary>Teknik detaylar (isteğe bağlı)</summary>
            <div>
              <span className="mono text-xs">Karar kodu: {verification.verdict}</span>
              <span className="mono text-xs">Kayıt: {verification.verification_id}</span>
            </div>
          </details>
        )}
      </div>
    </div>
  );
};
