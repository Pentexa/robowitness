"use client";

import React from "react";
import { Download, ShieldCheck } from "lucide-react";
import { API_BASE_URL } from "../lib/api";
import { VerificationRecord } from "../lib/types";

interface EvidencePanelProps {
  verification: VerificationRecord | null;
}

export const EvidencePanel: React.FC<EvidencePanelProps> = ({ verification }) => {
  if (!verification) return null;

  const downloadUrl = `${API_BASE_URL}/api/evidence/${verification.verification_id}/download`;

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <h3 className="rw-card-title">6. Evidence Package</h3>
        <span className="rw-badge mono">
          <ShieldCheck size={13} />
          SHA-256 SEALED
        </span>
      </div>

      <div className="rw-card-body">
        <p className="rw-note">
          Cryptographically sealed package: manifest, investigation hypothesis, 20-case
          holdout results, regression outcomes and markdown report.
        </p>
        <div className="rw-actions">
          <a
            id="btn-download-evidence"
            href={downloadUrl}
            className="rw-btn rw-btn-ghost"
            download
          >
            <Download size={15} /> Download evidence ZIP
          </a>
        </div>
      </div>
    </div>
  );
};
