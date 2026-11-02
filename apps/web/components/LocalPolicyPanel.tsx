"use client";

import React from "react";
import { Code2 } from "lucide-react";
import { LocalPolicyInfo } from "../lib/types";

interface LocalPolicyPanelProps {
  info: LocalPolicyInfo | null;
  selected: string;
  onSelect: (name: string) => void;
}

export const LocalPolicyPanel: React.FC<LocalPolicyPanelProps> = ({ info, selected, onSelect }) => {
  return (
    <section className="rw-section">
      <h3 className="rw-section-title">
        <Code2 size={14} /> Kendi Kodum (Yerel Politika)
      </h3>
      {!info ? (
        <p className="rw-summary">Yükleniyor…</p>
      ) : !info.enabled ? (
        <p className="rw-summary">
          Sunucuda kapalı. Açmak için <span className="mono">.env</span> içinde{" "}
          <span className="mono">RW_ALLOW_LOCAL_POLICY=on</span> yapıp arka ucu yeniden başlatın.
        </p>
      ) : (
        <>
          <select
            id="select-local-policy"
            className="rw-input"
            aria-label="Yerel politikalar"
            value={selected}
            onChange={(e) => onSelect(e.target.value)}
          >
            <option value="">— Kullanma (standart ayarlar) —</option>
            {info.policies.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}.py{p.description ? ` — ${p.description}` : ""}
              </option>
            ))}
          </select>
          <p className="rw-summary">
            Seçersen “Robotu Çalıştır” ve batarya,{" "}
            <span className="mono">backend/app/policies/local/</span> altındaki senin kodunla çalışır.
            <strong> Uyarı:</strong> Bu bir güvenlik kum havuzu değildir; yalnızca kendi yazdığın ve
            güvendiğin kodu koy. Meta AI'ın çözümleri için güvenli yol, yukarıdaki yama ve profil
            akışıdır. Kod ayrı bir süreçte çalışır; hata verirse veya 5 saniyeyi aşarsa koşu başarısız
            sayılır, sahte sonuç üretilmez.
          </p>
          {selected && (
            <p className="rw-summary" role="status">
              Aktif yerel politika: <strong>{selected}.py</strong>
            </p>
          )}
        </>
      )}
    </section>
  );
};
