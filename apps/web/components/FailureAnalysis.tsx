"use client";

import React, { useState } from "react";
import { InvestigationResponse, PolicyPatch } from "../lib/types";

interface FailureAnalysisProps {
  runId: string | null;
  investigation: InvestigationResponse | null;
  onInvestigate: () => Promise<void>;
  onApplyPatch: (patch: PolicyPatch) => void;
}

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
      setError(e instanceof Error ? e.message : "Investigation request failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rw-card">
      <div className="rw-card-head">
        <h3 className="rw-card-title">2. Failure Analysis</h3>
        {investigation && (
          <span className="rw-badge mono">
            <span className="dot" />
            {investigation.provenance}
          </span>
        )}
      </div>
      <div className="rw-card-body">
        {!runId && (
          <p className="rw-empty">Run a baseline simulation first to enable failure investigation.</p>
        )}
        {runId && !investigation && (
          <button
            id="btn-investigate"
            className="rw-btn rw-btn-primary rw-btn-block"
            onClick={handleInvestigate}
            disabled={isLoading}
          >
            {isLoading ? "Analyzing measured evidence…" : "Investigate baseline failure"}
          </button>
        )}
        {error && <p className="rw-err">{error}</p>}
        {investigation && (
          <>
            <div className="rw-spec">
              <div className="rw-spec-item">
                <span className="rw-spec-label">Measured failure tick</span>
                <span className="rw-spec-value mono">{investigation.failure_tick}</span>
              </div>
              <div className="rw-spec-item">
                <span className="rw-spec-label">Run</span>
                <span className="rw-spec-value mono text-xs">{investigation.run_id}</span>
              </div>
            </div>
            <div>
              <p className="rw-spec-label">Hypothesis (advisory — oracle decides)</p>
              <p className="text-sm">{investigation.hypothesis}</p>
            </div>
            <div>
              <p className="rw-spec-label">Grounded evidence</p>
              <p className="text-sm muted">{investigation.evidence_summary}</p>
            </div>
            <div>
              <p className="rw-spec-label">Suggested patch (whitelist fields only)</p>
              <pre className="rw-code">{JSON.stringify(investigation.suggested_patch, null, 2)}</pre>
            </div>
            <button
              id="btn-apply-patch"
              className="rw-btn rw-btn-ghost rw-btn-block"
              onClick={() => onApplyPatch(investigation.suggested_patch)}
            >
              Apply suggested patch to candidate
            </button>
          </>
        )}
      </div>
    </div>
  );
};
