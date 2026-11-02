"use client";

import React from "react";
import { CATEGORY_EN, DIFFICULTY_EN, SCENARIO_TEXT_EN, useLocale } from "../lib/i18n";
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
  const { locale, t } = useLocale();
  const active = entries.find((e) => e.scenario.id === activeScenarioId) ?? null;
  const groups = new Map<string, ScenarioCatalogEntry[]>();
  for (const entry of entries) {
    const key = entry.category || "Diğer";
    groups.set(key, [...(groups.get(key) ?? []), entry]);
  }
  const titleOf = (e: ScenarioCatalogEntry) =>
    locale === "en" ? (SCENARIO_TEXT_EN[e.scenario.id]?.title ?? e.title) : e.title;
  const descOf = (e: ScenarioCatalogEntry) =>
    locale === "en" ? (SCENARIO_TEXT_EN[e.scenario.id]?.description ?? e.description) : e.description;
  const categoryOf = (category: string) =>
    locale === "en" ? (CATEGORY_EN[category] ?? category) : category;

  return (
    <section className="rw-section">
      <h3 className="rw-section-title">
        {t("Senaryo Kütüphanesi")} ({entries.length})
      </h3>
      <select
        id="select-library-scenario"
        className="rw-input"
        aria-label={t("Kütüphaneden senaryo seçin")}
        value={active?.scenario.id ?? ""}
        disabled={disabled || entries.length === 0}
        onChange={(e) => {
          const entry = entries.find((x) => x.scenario.id === e.target.value);
          if (entry) onSelect(entry);
        }}
      >
        <option value="">{t("— Kütüphaneden seçin —")}</option>
        {Array.from(groups.entries()).map(([category, group]) => (
          <optgroup key={category} label={`${categoryOf(category)} (${group.length})`}>
            {group.map((e) => (
              <option key={e.scenario.id} value={e.scenario.id}>
                {titleOf(e)} — {e.scenario.obstacles.length} {t("engel")}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
      {active && (
        <p className="rw-summary">
          {descOf(active)}{" "}
          <strong>
            ({active.scenario.obstacles.length} {t("engel")}
            {locale === "en" && DIFFICULTY_EN[active.difficulty]
              ? ` · ${DIFFICULTY_EN[active.difficulty]}`
              : ""}
            )
          </strong>
        </p>
      )}
      {!active && (
        <p className="rw-summary">
          {t("Kalabalık insan trafiği için")} <strong>{t("Kalabalık Trafik")}</strong>{" "}
          {t("grubundan, en zor sınavlar için")} <strong>{t("Ultra Zor")}</strong>{" "}
          {t("grubundan seçin.")}
        </p>
      )}
    </section>
  );
};
