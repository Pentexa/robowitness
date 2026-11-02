"""Markdown report card for a battery run — every number traces to a run_id."""

from app.schemas.battery import BatteryResult

_STATUS = {
    "tr": {"PASS": "GEÇTİ", "FAIL": "KALDI", "INCONCLUSIVE": "BELİRSİZ"},
    "en": {"PASS": "PASS", "FAIL": "FAIL", "INCONCLUSIVE": "INCONCLUSIVE"},
}

_REASON = {
    "tr": {
        "COLLISION": "Çarpışma",
        "MIN_CLEARANCE_VIOLATION": "Güvenli mesafe ihlali (yakın geçiş olabilir)",
        "GOAL_NOT_REACHED": "Hedefe ulaşılamadı",
        "TIMEOUT": "Süre doldu",
        "STUCK": "Takılı kaldı",
    },
    "en": {
        "COLLISION": "Collision",
        "MIN_CLEARANCE_VIOLATION": "Safety clearance violation (may be a near-miss)",
        "GOAL_NOT_REACHED": "Goal not reached",
        "TIMEOUT": "Timeout",
        "STUCK": "Stuck",
    },
}


def generate_battery_report(result: BatteryResult, lang: str = "tr") -> str:
    lang = "en" if lang == "en" else "tr"
    status_tr = _STATUS[lang]
    reason_tr = _REASON[lang]
    s = result.summary
    if lang == "en":
        lines = [
            f"# Robot Exam Report Card — {result.robot_label}",
            "",
            f"- Report id: `{result.battery_id}`",
            f"- Robot: `{result.robot_id}`",
            f"- Policy: `{result.policy_id}`",
            f"- Date: {result.completed_at or result.created_at}",
            "- Source: Simulation (PyBullet) — every row traces to a real run (`run_id`).",
            "",
            "## Summary",
            "",
            f"- Scenarios: **{s.total}** — Passed: **{s.passed}**, Failed: **{s.failed}**, "
            f"Inconclusive: **{s.inconclusive}**",
            f"- Collisions: **{s.collisions}** · Near-misses (no crash but unsafe): "
            f"**{s.near_misses}**",
            f"- Worst (lowest) obstacle clearance: **{s.worst_clearance_m} m**",
            "",
            "## Scenarios",
            "",
            "| Scenario | Result | Reasons | Closest distance (m) | Goal | Duration (s) | Run |",
            "|---|---|---|---|---|---|---|",
        ]
        yes_no = ("Yes", "No")
        near_suffix = " (near-miss)"
        note = (
            "> Note: This report card is a simulation measurement, not a real-world "
            "safety approval. Passing it does not replace the separate 20-scenario "
            "frozen-holdout verification flow."
        )
    else:
        lines = [
            f"# Robot Sınav Karnesi — {result.robot_label}",
            "",
            f"- Karne kodu: `{result.battery_id}`",
            f"- Robot: `{result.robot_id}`",
            f"- Politika: `{result.policy_id}`",
            f"- Tarih: {result.completed_at or result.created_at}",
            "- Kaynak: Simülasyon (PyBullet) — her satır gerçek bir koşuya (`run_id`) bağlıdır.",
            "",
            "## Özet",
            "",
            f"- Toplam senaryo: **{s.total}** — Geçti: **{s.passed}**, Kaldı: **{s.failed}**, "
            f"Belirsiz: **{s.inconclusive}**",
            f"- Çarpışma: **{s.collisions}** · Yakın geçiş (çarpışmasız ama güvensiz): "
            f"**{s.near_misses}**",
            f"- En kötü (en düşük) engel mesafesi: **{s.worst_clearance_m} m**",
            "",
            "## Senaryolar",
            "",
            "| Senaryo | Sonuç | Nedenler | En yakın mesafe (m) | Hedef | Süre (sn) | Koşu |",
            "|---|---|---|---|---|---|---|",
        ]
        yes_no = ("Evet", "Hayır")
        near_suffix = " (yakın geçiş)"
        note = (
            "> Not: Bu karne simülasyon ölçümüdür; gerçek dünya güvenlik onayı değildir. "
            "Aday politika düzeltmelerinin 20'li gizli set onayı (ayrı doğrulama akışı) "
            "bu karneden bağımsızdır."
        )
    for e in result.entries:
        reasons = ", ".join(reason_tr.get(r, r) for r in e.reason_codes) or "—"
        if e.near_miss:
            reasons += near_suffix
        lines.append(
            f"| {e.title} (`{e.scenario_id}`) | {status_tr.get(e.oracle_status, e.oracle_status)} "
            f"| {reasons} | {e.metrics.min_clearance_m} "
            f"| {yes_no[0] if e.metrics.goal_reached else yes_no[1]} "
            f"| {e.metrics.sim_duration_s} | `{e.run_id}` |"
        )
    lines += ["", note, ""]
    return "\n".join(lines)
