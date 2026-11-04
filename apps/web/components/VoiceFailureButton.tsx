"use client";

import React, { useEffect, useRef, useState } from "react";
import { useLocale } from "../lib/i18n";

interface VoiceFailureButtonProps {
  disabled?: boolean;
  hasFailedRun: boolean;
  onInvestigate: () => Promise<void>;
}

// Minimal structural type for the Web Speech API (not in TS DOM lib).
interface SpeechRecognitionLike {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  onresult: ((event: { results: ArrayLike<ArrayLike<{ transcript: string }>> }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
}

function recognitionCtor(): (new () => SpeechRecognitionLike) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as Record<string, unknown>;
  const ctor = (w.SpeechRecognition ?? w.webkitSpeechRecognition) as
    | (new () => SpeechRecognitionLike)
    | undefined;
  return ctor ?? null;
}

/**
 * Voice shortcut into the REAL failure investigation. Speech only replaces
 * typing/clicking: the transcript never invents a failure. Investigation
 * opens solely when the oracle already marked the current run FAIL (the
 * backend additionally enforces this with 409 RUN_DID_NOT_FAIL).
 */
export const VoiceFailureButton: React.FC<VoiceFailureButtonProps> = ({
  disabled,
  hasFailedRun,
  onInvestigate,
}) => {
  const { t, dateLocale } = useLocale();
  const [supported, setSupported] = useState<boolean | null>(null);
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    setSupported(recognitionCtor() !== null);
    return () => {
      try {
        recognitionRef.current?.stop();
      } catch {
        /* already stopped */
      }
    };
  }, []);

  const handleClick = () => {
    const Ctor = recognitionCtor();
    if (!Ctor) {
      setSupported(false);
      setNote(t("Bu tarayıcı ses tanımayı desteklemiyor (Chrome veya Edge gerekir). Yazarak devam edebilirsiniz."));
      return;
    }
    if (listening) {
      recognitionRef.current?.stop();
      return;
    }
    setNote(null);
    setTranscript(null);
    const recognition = new Ctor();
    recognition.lang = dateLocale;
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onresult = (event) => {
      const text = event.results?.[0]?.[0]?.transcript?.trim() ?? "";
      if (!text) return;
      setTranscript(text);
      if (hasFailedRun) {
        onInvestigate()
          .then(() => setNote(t("Şimdi İncele sekmesinde arıza analizi açılıyor.")))
          .catch(() => setNote(t("Ses tanıma başlatılamadı")));
      } else {
        setNote(t("Investigation yalnızca FAIL alan koşumda açılır. Önce robotu çalıştırın; çarpma veya ihlal olursa sesli komut analizi başlatır."));
      }
    };
    recognition.onerror = (event) => {
      setListening(false);
      setNote(
        event.error === "not-allowed"
          ? t("Mikrofon izni gerekli")
          : t("Ses tanıma başlatılamadı"),
      );
    };
    recognition.onend = () => setListening(false);
    recognitionRef.current = recognition;
    try {
      recognition.start();
      setListening(true);
    } catch {
      setNote(t("Ses tanıma başlatılamadı"));
    }
  };

  return (
    <div className="rw-card">
      <div className="rw-card-body">
        <button
          type="button"
          className="rw-btn"
          onClick={handleClick}
          disabled={disabled || supported === false}
          aria-pressed={listening}
        >
          {listening ? `🎙️ ${t("Dinleniyor… söyleyin")}` : `🎙️ ${t("Arızayı Söyle")}`}
        </button>
        {supported === false && (
          <p className="rw-hint" role="status">
            {t("Bu tarayıcı ses tanımayı desteklemiyor (Chrome veya Edge gerekir). Yazarak devam edebilirsiniz.")}
          </p>
        )}
        {transcript && (
          <p className="rw-hint" role="status">
            {t("Sesin alındı")}: “{transcript}”
          </p>
        )}
        {note && supported !== false && (
          <p className="rw-hint" role="status">
            {note}
          </p>
        )}
      </div>
    </div>
  );
};
