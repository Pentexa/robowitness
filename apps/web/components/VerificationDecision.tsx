"use client";

import React from "react";
import { AlertTriangle, Check, Clock, X } from "lucide-react";
import { VerificationRecord } from "../lib/types";

interface VerificationDecisionProps {
  verification: VerificationRecord | null;
  isVerifying: boolean;
}

function verdictTone(verdict: string): "ok" | "bad" | "idle" {
  if (verdict === "VERIFIED_IN_SIMULATION") return "ok";
  if (verdict === "REJECTED") return "bad";
  return "idle";
}

export const VerificationDecision: React.FC<VerificationDecisionProps> = ({
  verification,
  isVerifying,
}) => {
  if (!verification && !isVerifying) {
    return (
      <div className="rw-card">
        <div className="rw-card-head">
          <h3 className="rw-card-title">4. Independent Verification</h3>
        </div>
        <div className="rw-card-body">
          <p className="rw-empty">Awaiting candidate fix submission to begin the verification protocol.</p>
        </div>
      </div>
    );
  }

  const verdict = verification?.verdict ?? "INCONCLUSIVE";
  const tone = verdictTone(verdict);

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <h3 className="rw-card-title">4. Independent Verification</h3>
        <span className={`rw-badge mono ${tone === "bad" ? "is-fail" : tone === "ok" ? "is-accent" : ""}`}>
          <span className="dot" />
          {isVerifying ? "RUNNING" : verdict}
        </span>
      </div>

      <div className="rw-card-body">
        <div className={`rw-verdict ${tone === "bad" ? "is-fail" : ""}`}>
          <span className="rw-verdict-label">Oracle verdict</span>
          <span className={`rw-verdict-value ${tone === "bad" ? "bad" : ""}`}>
            {tone === "ok" ? "✓ " : ""}{verdict}
          </span>
        </div>

        <div className="rw-gates">
          {(verification?.gates ?? []).map((g) => (
            <div key={g.gate_id} className={`rw-gate ${g.status === "FAIL" ? "is-fail" : ""}`}>
              <span className="rw-gate-icon">
                {g.status === "PASS" ? (
                  <Check size={16} color="#FFFFFF" />
                ) : g.status === "FAIL" ? (
                  <X size={16} color="#FF3366" />
                ) : g.status === "RUNNING" ? (
                  <Clock size={16} color="#94A3B8" />
                ) : (
                  <AlertTriangle size={16} color="#94A3B8" />
                )}
              </span>
              <div className="rw-gate-body">
                <div className="rw-gate-top">
                  <span className="rw-gate-name">{g.name}</span>
                  <span className={`rw-gate-status ${g.status === "FAIL" ? "bad" : "ok"}`}>
                    {g.status}
                  </span>
                </div>
                {g.reason_codes.length > 0 && (
                  <div className="rw-gate-reasons">{g.reason_codes.join(" · ")}</div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
