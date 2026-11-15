"""Normalize Spotify's account and extended-history schemas at the boundary."""

import json
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import Audit, Dataset, Play


class DataError(ValueError):
    """An input cannot be interpreted safely."""


def discover(inputs: Iterable[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in inputs:
        if path.is_dir():
            files.update(p.resolve() for p in path.rglob("StreamingHistory*.json"))
            files.update(p.resolve() for p in path.rglob("Streaming_History*.json"))
        elif path.is_file():
            files.add(path.resolve())
        else:
            raise DataError(f"Input does not exist: {path}")
    if not files:
        raise DataError("No history files found. Supply JSON files or a Spotify export directory.")
    return sorted(files)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DataError(f"{field} must be a non-empty string")
    return value.strip()


def normalize(row: Any) -> Play | None:
    if not isinstance(row, dict):
        raise DataError("row must be an object")
    extended = "ts" in row
    if extended:
        if "master_metadata_track_name" not in row:
            raise DataError("extended row is missing master_metadata_track_name")
        if row.get("master_metadata_track_name") is None:
            return None
        title = row.get("master_metadata_track_name")
        artist = row.get("master_metadata_album_artist_name")
        duration, timestamp = row.get("ms_played"), row.get("ts")
    else:
        title, artist = row.get("trackName"), row.get("artistName")
        duration, timestamp = row.get("msPlayed"), row.get("endTime")
    if isinstance(duration, bool) or not isinstance(duration, int) or duration < 0:
        raise DataError("duration must be a non-negative integer in milliseconds")
    timestamp = _text(timestamp, "timestamp")
    try:
        ended_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DataError(f"invalid timestamp: {timestamp!r}") from exc
    if ended_at.tzinfo is None:
        # Account exports omit an offset; assume UTC deterministically.
        ended_at = ended_at.replace(tzinfo=UTC)
    try:
        ended_at = ended_at.astimezone(UTC)
        ended_at - timedelta(milliseconds=duration)
    except (OverflowError, ValueError) as exc:
        raise DataError("play interval is outside the supported datetime range") from exc
    uri = row.get("spotify_track_uri") if extended else None
    if uri is not None:
        uri = _text(uri, "spotify_track_uri")
    return Play(ended_at, duration, _text(title, "track"), _text(artist, "artist"), uri)


def load(inputs: Iterable[Path], *, strict: bool = False, deduplicate: bool = False) -> Dataset:
    audit = Audit()
    plays: list[Play] = []
    seen: set[Play] = set()
    for path in discover(inputs):
        try:
            with path.open(encoding="utf-8-sig") as source:
                rows = json.load(source)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise DataError(f"Cannot read {path.name}: {exc}") from exc
        if not isinstance(rows, list):
            raise DataError(f"{path.name}: expected a JSON array")
        audit.files += 1
        for index, row in enumerate(rows, 1):
            audit.rows += 1
            try:
                play = normalize(row)
            except DataError as exc:
                message = f"{path.name}, row {index}: {exc}"
                if strict:
                    raise DataError(message) from exc
                audit.invalid += 1
                if len(audit.examples) < 5:
                    audit.examples.append(message)
                continue
            if play is None:
                audit.non_music += 1
                continue
            if deduplicate and play in seen:
                audit.duplicates += 1
                continue
            if deduplicate:
                seen.add(play)
            plays.append(play)
            audit.accepted += 1
    return Dataset(tuple(sorted(plays, key=lambda p: p.ended_at)), audit)
