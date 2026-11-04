"""Standalone portable HTML verification report.

One self-contained file: inline CSS, inline SVG charts, no external
requests. Every number comes from the recorded verification (DB row,
comparison.json, sealed telemetry); anything missing is stated, never
invented. All interpolated text is HTML-escaped.
"""

import html
import json
from pathlib import Path
from typing import List, Optional


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _svg_clearance_chart(
    baseline: List[float], candidate: List[float], limit: Optional[float]
) -> str:
    """Inline SVG: clearance over ticks for both runs + safety threshold."""
    series = [s for s in (baseline, candidate) if s]
    if not series:
        return '<p class="muted">No sealed telemetry available for a chart.</p>'
    width, height, pad = 720, 220, 28
    max_tick = max(len(s) for s in series)
    max_val = max(max(s) for s in series)
    if limit is not None:
        max_val = max(max_val, limit)
    max_val = max(max_val, 0.1)

    def points(values: List[float]) -> str:
        pts = []
        for i, v in enumerate(values):
            x = pad + (i / max(max_tick - 1, 1)) * (width - 2 * pad)
            y = height - pad - (v / max_val) * (height - 2 * pad)
            pts.append(f"{x:.1f},{y:.1f}")
        return " ".join(pts)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="Clearance chart">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
    ]
    if limit is not None:
        y = height - pad - (limit / max_val) * (height - 2 * pad)
        parts.append(
            f'<line x1="{pad}" y1="{y:.1f}" x2="{width - pad}" y2="{y:.1f}" '
            'stroke="#b3261e" stroke-dasharray="5 4" stroke-width="1.5"/>'
            f'<text x="{width - pad}" y="{y - 5:.1f}" font-size="11" fill="#b3261e" '
            f'text-anchor="end">min clearance {_esc(limit)} m</text>'
        )
    if baseline:
        parts.append(
            f'<polyline fill="none" stroke="#b3261e" stroke-width="1.6" '
            f'points="{points(baseline)}"/>'
        )
    if candidate:
        parts.append(
            f'<polyline fill="none" stroke="#1e7d32" stroke-width="1.6" '
            f'points="{points(candidate)}"/>'
        )
    parts.append(
        f'<text x="{pad}" y="16" font-size="11" fill="#b3261e">baseline</text>'
        f'<text x="{pad + 70}" y="16" font-size="11" fill="#1e7d32">candidate</text>'
        f'<text x="{pad}" y="{height - 6}" font-size="10" fill="#666">ticks →</text>'
        "</svg>"
    )
    return "".join(parts)


def _read_json(path: Path) -> Optional[dict]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_clearances(path: Path) -> List[float]:
    values: List[float] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    values.append(float(json.loads(line).get("clearance_m", 0.0)))
    except Exception:
        return []
    return values


def generate_verification_html(
    *,
    verification_id: str,
    verdict: str,
    baseline_run_id: str,
    candidate_policy: dict,
    gates: List[dict],
    created_at: str,
    artifact_dir: Path,
) -> str:
    comparison = _read_json(artifact_dir / "comparison.json") or {}
    hashes = _read_json(artifact_dir / "hashes.json") or {}
    investigation = _read_json(artifact_dir / "investigation.json") or {}
    baseline_dir = artifact_dir.parent.parent / "runs" / baseline_run_id
    baseline_clear = _read_clearances(baseline_dir / "telemetry.jsonl")
    candidate_clear = _read_clearances(artifact_dir / "telemetry_candidate.jsonl")
    scenario_doc = _read_json(baseline_dir / "scenario.json") or {}
    oracle_doc = scenario_doc.get("oracle", {}) if isinstance(scenario_doc, dict) else {}
    clearance_limit = oracle_doc.get("min_clearance_m")
    if not isinstance(clearance_limit, (int, float)):
        clearance_limit = None

    base_metrics = comparison.get("baseline", {}) if isinstance(comparison, dict) else {}
    cand_metrics = comparison.get("candidate", {}) if isinstance(comparison, dict) else {}

    gate_rows = "".join(
        "<tr>"
        f"<td>{_esc(g.get('gate_id', ''))}</td>"
        f"<td>{_esc(g.get('name', ''))}</td>"
        f'<td class="st-{_esc(str(g.get("status", "")).lower())}">'
        f"{_esc(g.get('status', ''))}</td>"
        f"<td>{_esc(', '.join(g.get('reason_codes', []) or []) or '—')}</td>"
        "</tr>"
        for g in gates
    )
    hash_rows = "".join(
        f'<tr><td>{_esc(name)}</td><td class="mono">{_esc(digest)}</td></tr>'
        for name, digest in sorted(hashes.items())
    )
    policy_rows = "".join(
        f"<tr><td>{_esc(k)}</td><td>{_esc(v)}</td></tr>"
        for k, v in sorted(candidate_policy.items())
    )

    def metric(m: dict, key: str) -> str:
        v = m.get(key)
        return _esc(v) if v is not None else "—"

    metric_rows = "".join(
        [
            "<tr><td>Minimum clearance (m)</td>"
            f"<td>{metric(base_metrics, 'min_clearance_m')}</td>"
            f"<td>{metric(cand_metrics, 'min_clearance_m')}</td></tr>",
            "<tr><td>Goal reached</td>"
            f"<td>{metric(base_metrics, 'goal_reached')}</td>"
            f"<td>{metric(cand_metrics, 'goal_reached')}</td></tr>",
            "<tr><td>Collision</td>"
            f"<td>{metric(base_metrics, 'collision_detected')}</td>"
            f"<td>{metric(cand_metrics, 'collision_detected')}</td></tr>",
            "<tr><td>Total ticks</td>"
            f"<td>{metric(base_metrics, 'total_ticks')}</td>"
            f"<td>{metric(cand_metrics, 'total_ticks')}</td></tr>",
        ]
    )

    chart = _svg_clearance_chart(baseline_clear, candidate_clear, clearance_limit)
    findings = investigation.get("hypothesis") or "No investigation recorded."

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RoboWitness Verification Report — {_esc(verification_id)}</title>
<style>
body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  margin: 2rem auto; max-width: 860px; padding: 0 1rem; color: #1c1e21; }}
h1 {{ font-size: 1.4rem; }}
h2 {{ font-size: 1.05rem; margin-top: 1.8rem; border-bottom: 2px solid #e4e6eb;
  padding-bottom: .3rem; }}
table {{ border-collapse: collapse; width: 100%; font-size: .85rem; }}
th, td {{ border: 1px solid #ccd0d5; padding: .35rem .5rem; text-align: left;
  vertical-align: top; }}
th {{ background: #f0f2f5; }}
.mono {{ font-family: ui-monospace, Consolas, monospace; font-size: .72rem;
  word-break: break-all; }}
.muted {{ color: #65676b; }}
.st-pass {{ color: #1e7d32; font-weight: 700; }}
.st-fail {{ color: #b3261e; font-weight: 700; }}
.st-inconclusive {{ color: #9e6a00; font-weight: 700; }}
.verdict {{ display: inline-block; padding: .3rem .7rem; border-radius: 4px;
  font-weight: 700; background: #f0f2f5; border: 1px solid #ccd0d5; }}
footer {{ margin-top: 2.5rem; font-size: .75rem; color: #65676b;
  border-top: 1px solid #e4e6eb; padding-top: .6rem; }}
</style>
</head>
<body>
<h1>RoboWitness — Independent Verification Report</h1>
<p><span class="verdict">{_esc(verdict)}</span></p>
<p class="muted">Verification <span class="mono">{_esc(verification_id)}</span> ·
baseline run <span class="mono">{_esc(baseline_run_id)}</span> · recorded {_esc(created_at)}.
This file is a portable rendering of the sealed evidence package; the package
itself (SHA-256 hashes below) remains the source of truth.</p>

<h2>Five verification gates</h2>
<table><thead><tr><th>Gate</th><th>Name</th><th>Status</th><th>Reason codes</th></tr></thead>
<tbody>{gate_rows}</tbody></table>

<h2>Measured outcome (paired runs)</h2>
<table><thead><tr><th>Metric</th><th>Baseline</th><th>Candidate</th></tr></thead>
<tbody>{metric_rows}</tbody></table>

<h2>Clearance over time (sealed telemetry)</h2>
{chart}

<h2>Findings</h2>
<p>{_esc(findings)}</p>

<h2>Candidate policy</h2>
<table><tbody>{policy_rows}</tbody></table>

<h2>Evidence integrity (SHA-256)</h2>
<table><thead><tr><th>File</th><th>SHA-256</th></tr></thead>
<tbody>{hash_rows or '<tr><td colspan="2">hashes.json not present</td></tr>'}</tbody>
</table>

<footer>Generated by RoboWitness. The oracle decided from measured telemetry;
the proposing AI never grades its own fix. Verify this report against the
sealed evidence package (Evidence Inspector or scripts/verify_evidence.py).</footer>
</body>
</html>"""
