"use client";

import React from "react";
import { Download, ShieldCheck } from "lucide-react";
import { VerificationRecord } from "../lib/types";

interface EvidencePanelProps {
  verification: VerificationRecord | null;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ verification }) => {
  if (!verification) return null;

  const downloadUrl = `/api/evidence/${verification.verification_id}/download`;

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">4. Evidence Package & Integrity</h3>
        <span className="badge badge-primary font-mono text-xs">
          <ShieldCheck size={14} className="inline mr-1" /> SHA-256 SEALED
        </span>
      </div>

      <div className="card-body">
        <div className="evidence-info">
          <p className="text-sm text-muted">
            Cryptographically sealed package with manifest, investigation hypothesis, 20-case holdout results, and markdown report.
          </p>

          <div className="mt-3 action-row">
            <a
              id="btn-download-evidence"
              href={downloadUrl}
              className="btn btn-secondary inline-flex items-center gap-2"
              download
            >
              <Download size={16} /> Download Evidence ZIP
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};
