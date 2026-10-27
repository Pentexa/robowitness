"use client";

import React from "react";
import { CheckCircle2, XCircle, AlertTriangle, Clock } from "lucide-react";
import { VerificationRecord } from "../lib/types";

interface VerificationDecisionProps {
  verification: VerificationRecord | null;
  isVerifying: boolean;
}

export const VerificationDecision: React.FC<VerificationDecisionProps> = ({
  verification,
  isVerifying,
}) => {
  if (!verification && !isVerifying) {
    return (
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">3. Independent Verification Outcome</h3>
        </div>
        <div className="card-body">
          <p className="text-muted">Awaiting candidate fix submission to begin verification protocol.</p>
        </div>
      </div>
    );
  }

  const verdict = verification?.verdict ?? "INCONCLUSIVE";
  const badgeClass =
    verdict === "VERIFIED_IN_SIMULATION"
      ? "badge-success"
      : verdict === "REJECTED"
      ? "badge-danger"
      : "badge-warning";

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">3. Independent Verification Protocol</h3>
        <span className={`badge ${badgeClass} font-mono text-sm`}>
          {isVerifying ? "RUNNING GATES" : verdict}
        </span>
      </div>

      <div className="card-body">
        <div className="gates-list">
          {verification?.gates.map((g) => {
            const isPass = g.status === "PASS";
            const isFail = g.status === "FAIL";
            return (
              <div key={g.gate_id} className="gate-item">
                <div className="gate-status-icon">
                  {isPass ? (
                    <CheckCircle2 className="text-success" size={18} />
                  ) : isFail ? (
                    <XCircle className="text-danger" size={18} />
                  ) : (
                    <AlertTriangle className="text-warning" size={18} />
                  )}
                </div>
                <div className="gate-content">
                  <div className="gate-title-row">
                    <span className="font-semibold text-sm">{g.name}</span>
                    <span className={`gate-status-tag ${isPass ? "text-success" : "text-danger"}`}>
                      {g.status}
                    </span>
                  </div>
                  {g.reason_codes.length > 0 && (
                    <div className="text-xs text-danger font-mono mt-1">
                      Reasons: {g.reason_codes.join(", ")}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
