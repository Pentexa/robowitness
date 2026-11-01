"use client";

import React from "react";
import { Check } from "lucide-react";

interface VerificationHistoryProps {
  history: Array<{ verification_id: string; verdict: string; baseline_run_id: string; created_at: string }>;
  activeId: string | null;
  onSelect: (verificationId: string) => void;
  onClear: () => void;
}

const VERDICT_SHORT: Record<string, string> = {
  VERIFIED_IN_SIMULATION: "KABUL EDİLDİ",
  REJECTED: "REDDEDİLDİ",
  INCONCLUSIVE: "BELİRSİZ",
};

export const VerificationHistory: React.FC<VerificationHistoryProps> = ({
  history,
  activeId,
  onSelect,
  onClear,
}) => {
  if (history.length === 0) return null;
  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">Geçmiş Sonuçlar</h3>
          <p className="rw-card-sub">Eski bir sonuca tıklayarak tekrar açabilirsiniz.</p>
        </div>
        <span className="rw-badge mono">{history.length} KAYIT</span>
      </div>
      <div className="rw-card-body">
        {history.map((h) => {
          const isActive = h.verification_id === activeId;
          const failed = h.verdict === "REJECTED";
          return (
            <button
              key={h.verification_id}
              className="rw-table-row"
              style={{
                gridTemplateColumns: "1fr auto",
                width: "100%",
                background: isActive ? "#e9e9e9" : "transparent",
                border: "none",
                borderBottom: "1px solid #e4e4e4",
                borderRadius: "3px",
                cursor: "pointer",
                textAlign: "left",
                color: "inherit",
                font: "inherit",
                padding: "7px 6px",
              }}
              onClick={() => (isActive ? onClear() : onSelect(h.verification_id))}
              title={isActive ? "Bu sonucu kapat" : "Bu sonucu aç"}
            >
              <span className="mono text-xs">
                {isActive ? "● " : "○ "} {h.created_at.slice(0, 10)} · {h.verification_id.slice(0, 14)}
              </span>
              <span className={`rw-gate-status ${failed ? "bad" : ""}`}>
                {h.verdict === "VERIFIED_IN_SIMULATION" ? (
                  <>
                    <Check size={12} style={{ display: "inline", verticalAlign: "-2px" }} />{" "}
                  </>
                ) : null}
                {VERDICT_SHORT[h.verdict] ?? h.verdict}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
