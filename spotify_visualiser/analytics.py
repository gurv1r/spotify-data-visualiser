"""Pure analytical core: no filesystem, network, or presentation dependencies."""

import math
from collections import Counter
from dataclasses import asdict
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .models import Dataset, Play


def _streak(days: list[date]) -> int:
    longest = current = 0
    previous: date | None = None
    for day in days:
        adjacent = previous is not None and day - previous == timedelta(days=1)
        current = current + 1 if adjacent else 1
        longest = max(longest, current)
        previous = day
    return longest


def analyse(
    dataset: Dataset,
    *,
    timezone: str = "UTC",
    start: date | None = None,
    end: date | None = None,
    min_ms: int = 0,
    session_gap_minutes: int = 30,
    top: int = 10,
) -> dict[str, Any]:
    if min_ms < 0 or session_gap_minutes < 0 or top < 1:
        raise ValueError("Thresholds must be non-negative and top must be positive")
    if start is not None and end is not None and start > end:
        raise ValueError("Start date must be on or before end date")
    zone = ZoneInfo(timezone)
    plays = [
        p
        for p in dataset.plays
        if p.milliseconds >= min_ms
        and (start is None or p.ended_at.astimezone(zone).date() >= start)
        and (end is None or p.ended_at.astimezone(zone).date() <= end)
    ]
    track_ms: Counter[tuple[str, str]] = Counter()
    track_count: Counter[tuple[str, str]] = Counter()
    artist_ms: Counter[str] = Counter()
    artist_count: Counter[str] = Counter()
    daily: Counter[str] = Counter()
    hourly = [[0 for _ in range(24)] for _ in range(7)]
    for play in plays:
        key = (play.track, play.artist)
        track_ms[key] += play.milliseconds
        track_count[key] += 1
        artist_ms[play.artist] += play.milliseconds
        artist_count[play.artist] += 1
        local = play.ended_at.astimezone(zone)
        daily[local.date().isoformat()] += play.milliseconds
        hourly[local.weekday()][local.hour] += play.milliseconds
    days = sorted(date.fromisoformat(d) for d in daily)
    trend = []
    if days:
        for offset in range((days[-1] - days[0]).days + 1):
            day = days[0] + timedelta(days=offset)
            trend.append({"date": day.isoformat(), "milliseconds": daily[day.isoformat()]})
    sessions = _sessions(plays, session_gap_minutes)
    entropy = -sum((n / len(plays)) * math.log2(n / len(plays)) for n in artist_count.values())
    total = sum(p.milliseconds for p in plays)
    return {
        "schema_version": 1,
        "parameters": {
            "timezone": timezone,
            "start": str(start) if start else None,
            "end": str(end) if end else None,
            "min_ms": min_ms,
            "session_gap_minutes": session_gap_minutes,
            "top": top,
        },
        "audit": asdict(dataset.audit),
        "summary": {
            "plays": len(plays),
            "milliseconds": total,
            "hours": total / 3_600_000,
            "unique_tracks": len(track_ms),
            "unique_artists": len(artist_ms),
            "active_days": len(days),
            "calendar_days": len(trend),
            "longest_streak_days": _streak(days),
            "artist_entropy_bits": entropy,
            "effective_artists": 2**entropy if plays else 0.0,
            "top_artist_share": max(artist_ms.values(), default=0) / total if total else 0.0,
            "session_count": len(sessions),
            "first_date": days[0].isoformat() if days else None,
            "last_date": days[-1].isoformat() if days else None,
        },
        "tracks": [
            {"track": t, "artist": a, "milliseconds": track_ms[t, a], "plays": track_count[t, a]}
            for t, a in sorted(track_ms, key=lambda k: (-track_ms[k], k))[:top]
        ],
        "artists": [
            {"artist": a, "milliseconds": artist_ms[a], "plays": artist_count[a]}
            for a in sorted(artist_ms, key=lambda k: (-artist_ms[k], k))[:top]
        ],
        "daily": trend,
        "weekday_hour_ms": hourly,
        "sessions": sessions,
    }


def _sessions(plays: list[Play], gap_minutes: int) -> list[dict[str, Any]]:
    # Infer intervals so long songs do not create false session breaks.
    intervals = sorted(
        (
            (p.ended_at - timedelta(milliseconds=p.milliseconds), p.ended_at, p.milliseconds)
            for p in plays
        ),
        key=lambda interval: interval[0],
    )
    sessions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    last_end = None
    for began, ended, duration in intervals:
        if last_end is None or began - last_end > timedelta(minutes=gap_minutes):
            current = {
                "start": began.isoformat(),
                "end": ended.isoformat(),
                "plays": 0,
                "milliseconds": 0,
            }
            sessions.append(current)
        assert current is not None
        last_end = max(last_end, ended) if last_end is not None else ended
        current["end"] = last_end.isoformat()
        current["plays"] += 1
        current["milliseconds"] += duration
    return sessions
