"""Portable reports: deterministic JSON and self-contained HTML with inline SVG."""

import json
from html import escape
from pathlib import Path
from typing import Any


def json_report(report: dict[str, Any]) -> str:
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"


def _trend(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return '<p class="muted">No plays match the selected filters.</p>'
    peak = max((r["milliseconds"] for r in rows), default=0) or 1
    points = " ".join(
        f"{32 + i * 876 / max(1, len(rows) - 1):.2f},{176 - r['milliseconds'] / peak * 148:.2f}"
        for i, r in enumerate(rows)
    )
    return (
        '<svg viewBox="0 0 940 210" role="img" aria-label="Daily listening minutes">'
        '<path d="M32 28H908 M32 102H908 M32 176H908" stroke="#27322f"/>'
        f'<polyline points="{points}" fill="none" stroke="#78efb0" stroke-width="3"/>'
        + (
            f'<circle cx="32" cy="{176 - rows[0]["milliseconds"] / peak * 148:.2f}" '
            'r="4" fill="#78efb0"/>'
            if len(rows) == 1
            else ""
        )
        + f'<text x="32" y="16">Peak {peak / 60000:.1f} min/day</text>'
        f'<text x="32" y="202">{escape(rows[0]["date"])}</text>'
        f'<text x="908" y="202" text-anchor="end">{escape(rows[-1]["date"])}</text></svg>'
    )


def _heatmap(grid: list[list[int]]) -> str:
    peak = max((value for row in grid for value in row), default=0) or 1
    cells = []
    for day, label in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
        cells.append(f'<text x="0" y="{47 + day * 25}">{label}</text>')
        for hour, value in enumerate(grid[day]):
            opacity = 0.08 + 0.92 * value / peak
            cells.append(
                f'<rect x="{42 + hour * 36}" y="{32 + day * 25}" width="30" height="19" '
                f'rx="3" fill="#78efb0" opacity="{opacity:.3f}">'
                f"<title>{label} {hour:02d}:00: {value / 60000:.1f} minutes</title></rect>"
            )
    labels = "".join(f'<text x="{42 + h * 36}" y="20">{h:02d}</text>' for h in range(0, 24, 3))
    return (
        '<svg viewBox="0 0 940 215" role="img" '
        'aria-label="Listening time by weekday and hour; brighter cells mean more minutes">'
        + labels
        + "".join(cells)
        + "</svg>"
    )


def html_report(report: dict[str, Any]) -> str:
    s, audit, params = report["summary"], report["audit"], report["parameters"]
    metrics = [
        (f"{s['hours']:,.1f}", "hours listened"),
        (f"{s['plays']:,}", "play events"),
        (f"{s['unique_artists']:,}", "artists"),
        (str(s["longest_streak_days"]), "day streak"),
    ]
    cards = "".join(
        f'<div class="metric"><strong>{v}</strong><span>{label}</span></div>'
        for v, label in metrics
    )
    tracks = "".join(
        f"<tr><td>{i}</td><td>{escape(r['track'])}<small>{escape(r['artist'])}</small></td>"
        f"<td>{r['plays']:,}</td><td>{r['milliseconds'] / 60000:,.1f}</td></tr>"
        for i, r in enumerate(report["tracks"], 1)
    )
    peak = max((r["milliseconds"] for r in report["artists"]), default=0) or 1
    artists = "".join(
        f'<li><div class="artist-label"><span>{escape(r["artist"])}</span>'
        f"<span>{r['milliseconds'] / 60000:,.1f} min</span></div>"
        f'<div class="bar"><div style="width:{r["milliseconds"] / peak * 100:.2f}%"></div>'
        "</div></li>"
        for r in report["artists"]
    )
    diagnostics = "".join(f"<li>{escape(e)}</li>" for e in audit["examples"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Listening atlas · Spotify Data Visualiser</title>
<style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif;background:#0b1210;color:#edf5ef}}
*{{box-sizing:border-box}}body{{margin:0}}main{{max-width:1120px;margin:auto;padding:56px 28px}}
.eyebrow{{color:#78efb0;letter-spacing:.16em;font-size:12px;font-weight:700;text-transform:uppercase}}
h1{{font-size:clamp(38px,7vw,68px);letter-spacing:-.06em;margin:14px 0}}h2{{font-size:20px;margin:0 0 22px}}
p{{line-height:1.6}}.muted,small,footer{{color:#a0b4a8}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:36px 0}}
.metric,section{{border:1px solid #293c31;background:#111e17;border-radius:16px;padding:24px}}
.metric strong{{display:block;font-size:36px;font-weight:500}}.metric span{{font-size:13px;color:#a0b4a8}}
section{{margin-bottom:20px}}.columns{{display:grid;grid-template-columns:1.2fr 1fr;gap:20px}}
.chart{{overflow-x:auto}}svg{{width:100%;min-width:600px;height:auto}}svg text{{fill:#a0b4a8;font:12px system-ui,sans-serif}}
.table-wrap{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;padding:12px 8px;border-bottom:1px solid #293c31}}th{{color:#a0b4a8;font-weight:500}}
small{{display:block;margin-top:4px}}td:first-child{{color:#78efb0}}td:nth-last-child(-n+2){{text-align:right}}
ul{{padding-left:20px}}.artists{{list-style:none;padding:0}}.artists li{{margin-bottom:24px}}
.artist-label{{display:flex;justify-content:space-between;gap:16px;font-size:14px;margin-bottom:10px}}
.bar{{height:5px;background:#293c31;border-radius:5px}}.bar div{{height:100%;background:#78efb0;border-radius:5px}}
.note{{font-size:13px;line-height:1.7;color:#a0b4a8}}footer{{font-size:12px;margin-top:30px}}
@media(max-width:720px){{main{{padding:32px 16px}}.metrics{{grid-template-columns:repeat(2,1fr)}}.columns{{display:block}}section{{padding:18px}}}}
@media print{{:root{{color-scheme:light;background:white;color:black}}section,.metric{{background:white;border-color:#aaa}}.columns{{display:block}}section{{break-inside:avoid}}}}
</style></head><body><main>
<div class="eyebrow">Spotify Data Visualiser / Local analytics</div><h1>Your listening atlas.</h1>
<p class="muted">{escape(str(s["first_date"] or "No dates"))} — {escape(str(s["last_date"] or "No dates"))}
 · {escape(params["timezone"])} · {s["active_days"]} active days</p>
<div class="metrics">{cards}</div>
<section><h2>The daily rhythm</h2>{_trend(report["daily"])}
<p class="note">All calendar days are included. Duration is attributed to the event’s end date.</p></section>
<div class="columns"><section><h2>Tracks on repeat</h2><div class="table-wrap"><table>
<thead><tr><th scope="col">#</th><th scope="col">Track / artist</th><th scope="col">Plays</th><th scope="col">Minutes</th></tr></thead>
<tbody>{tracks}</tbody></table></div></section><section><h2>Artist rotation</h2><ul class="artists">{artists}</ul></section></div>
<section><h2>When you listen</h2>{_heatmap(report["weekday_hour_ms"])}
<p class="note">Brighter cells represent more listening minutes. Hours use {escape(params["timezone"])}; hover a cell for its value.</p></section>
<section><h2>Beyond the leaderboard</h2><p>{s["session_count"]} inferred sessions · {s["unique_tracks"]} unique tracks
 · {s["effective_artists"]:.2f} effective artists · {s["top_artist_share"]:.1%} of time with the top artist.</p>
<p class="note">Effective artists = 2 raised to Shannon entropy of artist play counts. Session boundaries use
an idle gap greater than {params["session_gap_minutes"]} minutes between inferred playback intervals.
Sessions are estimates; overlapping device activity is not removed.</p></section>
<section><h2>Data provenance</h2><p class="note">{audit["files"]} files · {audit["rows"]} rows read ·
{audit["accepted"]} music events accepted before filters · {audit["invalid"]} invalid ·
{audit["non_music"]} non-music · {audit["duplicates"]} duplicates removed.
Minimum duration: {params["min_ms"]} ms. Date filter: {escape(str(params["start"] or "open"))} to {escape(str(params["end"] or "open"))}.</p>
<ul class="note">{diagnostics}</ul></section>
<footer>Generated offline by Spotify Data Visualiser v2 · No network requests, external fonts, or tracking.</footer>
</main></body></html>"""


def write_report(report: dict[str, Any], output: Path, format: str) -> None:
    content = html_report(report) if format == "html" else json_report(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
