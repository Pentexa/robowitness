"""Markdown report card for a battery run — every number traces to a run_id."""

from app.schemas.battery import BatteryResult

_STATUS_TR = {"PASS": "GEÇTİ", "FAIL": "KALDI", "INCONCLUSIVE": "BELİRSİZ"}

_REASON_TR = {
    "COLLISION": "Çarpışma",
    "MIN_CLEARANCE_VIOLATION": "Güvenli mesafe ihlali (yakın geçiş olabilir)",
    "GOAL_NOT_REACHED": "Hedefe ulaşılamadı",
    "TIMEOUT": "Süre doldu",
    "STUCK": "Takılı kaldı",
}


def generate_battery_report(result: BatteryResult) -> str:
    s = result.summary
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
    for e in result.entries:
        reasons = ", ".join(_REASON_TR.get(r, r) for r in e.reason_codes) or "—"
        if e.near_miss:
            reasons += " (yakın geçiş)"
        lines.append(
            f"| {e.title} (`{e.scenario_id}`) | {_STATUS_TR.get(e.oracle_status, e.oracle_status)} "
            f"| {reasons} | {e.metrics.min_clearance_m} "
            f"| {'Evet' if e.metrics.goal_reached else 'Hayır'} "
            f"| {e.metrics.sim_duration_s} | `{e.run_id}` |"
        )
    lines += [
        "",
        "> Not: Bu karne simülasyon ölçümüdür; gerçek dünya güvenlik onayı değildir. "
        "Aday politika düzeltmelerinin 20'li gizli set onayı (ayrı doğrulama akışı) "
        "bu karneden bağımsızdır ve bugüne dek tam onay alınamamıştır.",
        "",
    ]
    return "\n".join(lines)
