"use client";

import React, { useEffect, useState } from "react";
import { BookmarkPlus, Trash2 } from "lucide-react";
import { createPolicyProfile, deletePolicyProfile, fetchPolicyProfiles } from "../lib/api";
import { PolicyConfig, PolicyProfile } from "../lib/types";

interface PolicyProfilesProps {
  candidatePolicy: PolicyConfig;
  onSelectProfile: (policy: PolicyConfig) => void;
}

export const PolicyProfiles: React.FC<PolicyProfilesProps> = ({
  candidatePolicy,
  onSelectProfile,
}) => {
  const [profiles, setProfiles] = useState<PolicyProfile[]>([]);
  const [selectedId, setSelectedId] = useState<string>("");
  const [newName, setNewName] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const refresh = async () => setProfiles(await fetchPolicyProfiles());

  useEffect(() => {
    refresh().catch(() => setError("Profiller yüklenemedi."));
  }, []);

  const selected = profiles.find((p) => p.profile_id === selectedId) ?? null;

  const handleSelect = (profile: PolicyProfile) => {
    setSelectedId(profile.profile_id);
    onSelectProfile({ ...profile.policy });
    setNotice(`Profil uygulandı: ${profile.name}`);
    setError(null);
  };

  const handleSave = async () => {
    if (!newName.trim()) {
      setError("Profile bir isim verin.");
      return;
    }
    try {
      const created = await createPolicyProfile({
        name: newName.trim(),
        description: "Kullanıcının kaydettiği ayarlar",
        policy: { ...candidatePolicy, id: `candidate-${Date.now()}` },
      });
      setNewName("");
      setSelectedId(created.profile_id);
      await refresh();
      setNotice(`Profil kaydedildi: ${created.name}`);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Profil kaydedilemedi");
    }
  };

  const handleDelete = async (profile: PolicyProfile) => {
    try {
      await deletePolicyProfile(profile.profile_id);
      setSelectedId("");
      await refresh();
      setNotice(`Profil silindi: ${profile.name}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Profil silinemedi");
    }
  };

  return (
    <section className="rw-section">
      <h3 className="rw-section-title">Ayar Profilleri</h3>
      <div className="rw-btn-row">
        <select
          id="select-policy-profile"
          className="rw-input"
          style={{ flex: 1 }}
          aria-label="Ayar profilleri"
          value={selectedId}
          onChange={(e) => {
            const p = profiles.find((x) => x.profile_id === e.target.value);
            if (p) handleSelect(p);
          }}
        >
          <option value="">— Profil seçin —</option>
          {profiles.map((p) => (
            <option key={p.profile_id} value={p.profile_id}>
              {p.name}
              {p.source === "user" ? " (benim)" : ""}
            </option>
          ))}
        </select>
        {selected?.source === "user" && (
          <button className="rw-btn rw-btn-ghost rw-btn-sm" onClick={() => handleDelete(selected)}>
            <Trash2 size={14} /> Sil
          </button>
        )}
      </div>
      {selected && (
        <p className="rw-summary mono">
          hız {selected.policy.max_speed_mps} · mesafe {selected.policy.safe_distance_m} · tepki{" "}
          {selected.policy.reaction_margin_m} · fren {selected.policy.brake_gain} · tahmin{" "}
          {selected.policy.obstacle_prediction_horizon_s} sn
        </p>
      )}
      <div className="rw-btn-row">
        <input
          className="rw-input"
          style={{ flex: 1 }}
          placeholder="Şu anki ayarlara isim verin"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
        />
        <button id="btn-save-profile" className="rw-btn rw-btn-ghost rw-btn-sm" onClick={handleSave}>
          <BookmarkPlus size={14} /> Profil Olarak Kaydet
        </button>
      </div>
      {error && <p className="rw-err">{error}</p>}
      {notice && <p className="rw-summary">{notice}</p>}
    </section>
  );
};
