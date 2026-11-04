"use client";

import React, { useState } from "react";
import { inspectEvidenceZip } from "../lib/api";
import { useLocale } from "../lib/i18n";
import { EvidenceInspectReport } from "../lib/types";

const STATUS_LABEL: Record<string, string> = {
  OK: "OK",
  MISMATCH: "MISMATCH",
  MISSING: "MISSING",
  NOT_SEALED: "NOT_SEALED",
};

/**
 * Evidence Inspector: upload an evidence ZIP and re-verify it independently
 * in the browser flow — the server recomputes every SHA-256 from the bytes
 * you provide. A tampered or incomplete package fails here even if it was
 * produced by this very system.
 */
export const EvidenceInspector: React.FC = () => {
  const { t } = useLocale();
  const [report, setReport] = useState<EvidenceInspectReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string>("");

  const handleFile = async (file: File | null) => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setReport(null);
    setFileName(file.name);
    try {
      const dataUrl = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result ?? ""));
        reader.onerror = () => reject(new Error("file read failed"));
        reader.readAsDataURL(file);
      });
      const base64 = dataUrl.split(",", 2)[1] ?? "";
      const result = await inspectEvidenceZip(file.name, base64);
      setReport(result);
    } catch {
      setError(t("Kanıt paketi incelenemedi."));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <div>
          <h3 className="rw-card-title">{t("Kanıt Denetçisi")}</h3>
          <p className="rw-card-sub">
            {t("Bir kanıt ZIP'ini yükleyin; bütünlük, eksik dosyalar ve SHA-256 parmak izleri bağımsız olarak yeniden hesaplanır.")}
          </p>
        </div>
        {report && (
          <span className={`rw-badge mono ${report.ok ? "is-pass" : "is-fail"}`}>
            {report.ok ? t("BÜTÜNLÜK TAM") : t("BÜTÜNLÜK BOZUK")}
          </span>
        )}
      </div>
      <div className="rw-card-body">
        <label className="rw-btn rw-btn-block" htmlFor="input-evidence-zip">
          {busy ? t("İnceleniyor…") : t("Kanıt ZIP'i Seç")}
        </label>
        <input
          id="input-evidence-zip"
          type="file"
          accept=".zip,application/zip"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
        />
        {fileName && <p className="rw-hint mono">{fileName}</p>}
        {error && <p className="rw-err">{error}</p>}
        {report && (
          <div>
            <p className="rw-hint">
              {t("Paket tipi")}: {report.package_type}
              {report.package_id ? ` · ${report.package_id}` : ""}
              {report.verdict ? ` · ${report.verdict}` : ""}
              {report.oracle_status ? ` · ${report.oracle_status}` : ""} · {report.file_count}{" "}
              {t("dosya")}
            </p>
            {report.errors.length > 0 && (
              <p className="rw-err">{report.errors.join(" · ")}</p>
            )}
            <table className="rw-table">
              <thead>
                <tr>
                  <th>{t("Dosya")}</th>
                  <th>{t("Durum")}</th>
                  <th>SHA-256</th>
                </tr>
              </thead>
              <tbody>
                {report.files.map((f) => (
                  <tr key={f.name}>
                    <td className="mono">{f.name}</td>
                    <td className={`rw-file-status is-${f.status.toLowerCase()}`}>
                      {STATUS_LABEL[f.status] ?? f.status}
                    </td>
                    <td className="mono rw-hash-cell">{f.sha256 ? `${f.sha256.slice(0, 16)}…` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
