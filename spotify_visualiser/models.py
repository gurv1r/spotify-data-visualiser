"""Immutable domain types shared by ingestion and analysis."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Play:
    ended_at: datetime
    milliseconds: int
    track: str
    artist: str
    uri: str | None = None


@dataclass(slots=True)
class Audit:
    files: int = 0
    rows: int = 0
    accepted: int = 0
    invalid: int = 0
    non_music: int = 0
    duplicates: int = 0
    examples: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Dataset:
    plays: tuple[Play, ...]
    audit: Audit
