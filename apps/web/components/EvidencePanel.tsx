"use client";

import React from "react";
import { Download } from "lucide-react";
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
        <div>
          <h3 className="rw-card-title">Sonuç Raporu</h3>
          <p className="rw-card-sub">Bütün testlerin mühürlü sonuç dosyası.</p>
        </div>
        <span className="rw-badge mono">MÜHÜRLÜ</span>
      </div>
      <div className="rw-card-body">
        <p className="rw-note">
          Bu dosyayı indirip saklayabilirsiniz. Dosyanın sonradan değiştirilip değiştirilmediği özel bir
          parmak iziyle (SHA-256) anlaşılabilir; yani rapor, sonucu kanıtlamak için kullanılabilir.
        </p>
        <a id="btn-download-evidence" href={downloadUrl} className="rw-btn rw-btn-primary rw-btn-block" download>
          <Download size={15} /> Raporu İndir (.zip)
        </a>
        <details className="rw-details">
          <summary>Teknik detaylar (isteğe bağlı)</summary>
          <div>
            <span className="mono text-xs">Kayıt: {verification.verification_id}</span>
            <span className="mono text-xs">Klasör: {verification.artifact_dir}</span>
          </div>
        </details>
      </div>
    </div>
  );
};
