"use client";

import React from "react";
import { ScenarioCatalogEntry } from "../lib/types";

interface ScenarioLibraryProps {
  entries: ScenarioCatalogEntry[];
  activeScenarioId: string | null;
  onSelect: (entry: ScenarioCatalogEntry) => void;
  disabled: boolean;
}

export const ScenarioLibrary: React.FC<ScenarioLibraryProps> = ({
  entries,
  activeScenarioId,
  onSelect,
  disabled,
}) => {
  const active = entries.find((e) => e.scenario.id === activeScenarioId) ?? null;
  const groups = new Map<string, ScenarioCatalogEntry[]>();
  for (const entry of entries) {
    const key = entry.category || "Diğer";
    groups.set(key, [...(groups.get(key) ?? []), entry]);
  }
  return (
    <section className="rw-section">
      <h3 className="rw-section-title">Senaryo Kütüphanesi ({entries.length})</h3>
      <select
        id="select-library-scenario"
        className="rw-input"
        aria-label="Kütüphaneden senaryo seçin"
        value={active?.scenario.id ?? ""}
        disabled={disabled || entries.length === 0}
        onChange={(e) => {
          const entry = entries.find((x) => x.scenario.id === e.target.value);
          if (entry) onSelect(entry);
        }}
      >
        <option value="">— Kütüphaneden seçin —</option>
        {Array.from(groups.entries()).map(([category, group]) => (
          <optgroup key={category} label={`${category} (${group.length})`}>
            {group.map((e) => (
              <option key={e.scenario.id} value={e.scenario.id}>
                {e.title} — {e.scenario.obstacles.length} engel
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      {active && (
        <p className="rw-summary">
          {active.description} <strong>({active.scenario.obstacles.length} engel)</strong>
        </p>
      )}
      {!active && (
        <p className="rw-summary">
          Kalabalık insan trafiği için <strong>Kalabalık Trafik</strong> grubundan, en zor sınavlar için{" "}
          <strong>Ultra Zor</strong> grubundan seçin.
        </p>
      )}
    </section>
  );
};
