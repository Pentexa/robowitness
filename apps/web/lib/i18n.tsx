"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { EN } from "./locales/en";

export type Locale = "en" | "tr";

/**
 * i18n design: Turkish source strings are the keys. In Turkish mode the key
 * renders as-is; in English mode the EN dictionary provides the translation
 * (falling back to the key so a missing entry is visible, never silent).
 * Default locale is English (the project's primary language); the choice is
 * persisted in localStorage ("rw_locale").
 */
interface LocaleContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
  dateLocale: string;
}

const LocaleContext = createContext<LocaleContextValue>({
  locale: "en",
  setLocale: () => undefined,
  t: (key) => EN[key] ?? key,
  dateLocale: "en-US",
});

export const LocaleProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    try {
      const saved = localStorage.getItem("rw_locale");
      if (saved === "tr" || saved === "en") setLocaleState(saved);
    } catch {
      /* keep default */
    }
  }, []);

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    try {
      localStorage.setItem("rw_locale", next);
    } catch {
      /* ignore */
    }
  }, []);

  const t = useCallback(
    (key: string) => (locale === "en" ? (EN[key] ?? key) : key),
    [locale]
  );

  return (
    <LocaleContext.Provider
      value={{ locale, setLocale, t, dateLocale: locale === "tr" ? "tr-TR" : "en-US" }}
    >
      {children}
    </LocaleContext.Provider>
  );
};

export function useLocale(): LocaleContextValue {
  return useContext(LocaleContext);
}

/** Scenario catalog text (titles/descriptions live in backend JSON as TR). */
export const SCENARIO_TEXT_EN: Record<string, { title: string; description: string }> = {
  "RW-REF-001": {
    title: "Reference Test",
    description: "Canonical latency scenario: a fast crossing obstacle against 450 ms delayed sensing.",
  },
  "RW-LIB-001": {
    title: "Narrow Corridor",
    description: "Thread a narrow gap between two static obstacles without breaching the safety distance.",
  },
  "RW-LIB-002": {
    title: "Slalom",
    description: "Pass three staggered static obstacles without zigzagging into the safety margin.",
  },
  "RW-LIB-003": {
    title: "Diagonal Crossing",
    description: "Corner-to-corner drive past static obstacles sitting on the direct line.",
  },
  "RW-LIB-004": {
    title: "Head-On Obstacle",
    description: "An obstacle drives straight at the robot in its own lane.",
  },
  "RW-LIB-005": {
    title: "Diagonal Cut",
    description: "An obstacle cuts diagonally across the robot's path; timing is everything.",
  },
  "RW-LIB-006": {
    title: "High Sensor Latency",
    description: "800 ms sensor latency with a fast moving obstacle; a harder reference variant.",
  },
  "RW-LIB-007": {
    title: "Noisy Sensor",
    description: "Evade a moving obstacle while measurements are heavily noisy.",
  },
  "RW-LIB-008": {
    title: "Dual Moving Obstacles",
    description: "Two moving obstacles cut the path from opposite directions.",
  },
  "RW-LIB-009": {
    title: "Empty Corridor (Control)",
    description: "Obstacle-free control scenario; a healthy robot must reach the goal.",
  },
  "RW-LIB-010": {
    title: "Slow Traffic",
    description: "A slow obstacle crosses the path; balance early detection against waiting.",
  },
  "RW-ULTRA-001": {
    title: "Ultra: 900 ms Latency Wall",
    description: "Nearly a second of sensor delay against a fast crosser; the baseline breaches clearance.",
  },
  "RW-ULTRA-002": {
    title: "Ultra: Dual Onslaught",
    description: "Two fast movers cut the path from opposite directions; the baseline collides.",
  },
  "RW-ULTRA-003": {
    title: "Ultra: Double Diagonal",
    description: "Two obstacles share one corridor on diagonal routes; timing is everything.",
  },
  "RW-ULTRA-004": {
    title: "Ultra: Noise Storm",
    description: "Maximum sensor noise (0.20 m) plus latency against a fast obstacle.",
  },
  "RW-ULTRA-005": {
    title: "Ultra: Goal Guardian",
    description: "One obstacle on the path, one guarding the goal; the baseline never arrives.",
  },
  "RW-CROWD-001": {
    title: "Crowd: Crossing Streams",
    description: "Three pedestrian lanes cut the path in sequence; thread the gaps.",
  },
  "RW-CROWD-002": {
    title: "Crowd: Two-Way Corridor",
    description: "Pedestrian traffic in two opposing lanes; take the thin middle corridor.",
  },
  "RW-CROWD-003": {
    title: "Crowd: Goal Front",
    description: "Pedestrians on guard in front of the goal; mistime it and you collide.",
  },
  "RW-CROWD-004": {
    title: "Crowd: Market Square",
    description: "Five pedestrians on diagonal routes form market chaos; the baseline crashes early.",
  },
  "RW-CROWD-005": {
    title: "Crowd: Rush Hour",
    description: "Pedestrians running at 0.8-0.9 m/s with half a second of sensor delay; a reflex exam.",
  },
};

export const DIFFICULTY_EN: Record<string, string> = {
  Kolay: "Easy",
  Orta: "Medium",
  Zor: "Hard",
  Ultra: "Ultra",
  Kalabalık: "Crowd",
};

export const CATEGORY_EN: Record<string, string> = {
  "Sabit Engel": "Static Obstacle",
  "Hareketli Engel": "Moving Obstacle",
  Sensör: "Sensor",
  Kontrol: "Control",
  "Ultra Zor": "Ultra Hard",
  "Kalabalık Trafik": "Crowd Traffic",
};
