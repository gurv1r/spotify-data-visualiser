"""Command-line orchestration; analytical functions remain directly importable."""

import argparse
import sys
from datetime import date
from pathlib import Path
from zoneinfo import ZoneInfoNotFoundError

from . import __version__
from .analytics import analyse
from .ingest import DataError, discover, load
from .report import json_report, write_report


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Analyse Spotify exports locally; no account required.")
    p.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        default=[Path(".")],
        help="JSON files or export directories (default: current directory)",
    )
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--timezone", default="UTC", help="IANA zone, e.g. Europe/London")
    p.add_argument("--start", type=date.fromisoformat, help="Inclusive local date: YYYY-MM-DD")
    p.add_argument("--end", type=date.fromisoformat, help="Inclusive local date: YYYY-MM-DD")
    p.add_argument("--min-ms", type=int, default=0, help="Minimum listening duration per event")
    p.add_argument("--session-gap", type=int, default=30, help="Idle minutes before a new session")
    p.add_argument("--top", type=int, default=10, help="Number of leaderboard entries")
    p.add_argument("--strict", action="store_true", help="Fail on the first invalid music row")
    p.add_argument("--deduplicate", action="store_true", help="Remove exact normalized duplicates")
    p.add_argument("--format", choices=("text", "json", "html"), default="text")
    p.add_argument("--output", type=Path, help="Write JSON or HTML report to this file")
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if args.format == "html" and args.output is None:
        p.error("--format html requires --output")
    if args.output is not None and args.format == "text":
        p.error("--output requires --format json or html")
    if args.top < 1 or args.min_ms < 0 or args.session_gap < 0:
        p.error("--top must be positive; --min-ms and --session-gap must be non-negative")
    try:
        dataset = load(args.inputs, strict=args.strict, deduplicate=args.deduplicate)
        report = analyse(
            dataset,
            timezone=args.timezone,
            start=args.start,
            end=args.end,
            min_ms=args.min_ms,
            session_gap_minutes=args.session_gap,
            top=args.top,
        )
        report["parameters"]["deduplicate"] = args.deduplicate
        report["parameters"]["strict"] = args.strict
        if args.output:
            if args.output.resolve() in set(discover(args.inputs)):
                raise DataError("Output must not overwrite an input file")
            write_report(report, args.output, args.format)
            print(f"Wrote {args.format.upper()} report: {args.output}")
        elif args.format == "json":
            print(json_report(report), end="")
        else:
            s = report["summary"]
            print(
                f"{s['plays']:,} plays | {s['hours']:,.2f} hours | "
                f"{s['unique_artists']} artists | {s['session_count']} sessions"
            )
            print(
                f"Longest streak: {s['longest_streak_days']} days | "
                f"Effective artists: {s['effective_artists']:.2f}"
            )
            for i, row in enumerate(report["tracks"], 1):
                print(
                    f"{i:2}. {row['track']} — {row['artist']} | "
                    f"{row['milliseconds'] / 60000:.1f} min | {row['plays']} plays"
                )
        a = dataset.audit
        print(
            f"Input audit: {a.rows} rows, {a.accepted} accepted, {a.invalid} invalid, "
            f"{a.non_music} non-music, {a.duplicates} duplicates removed",
            file=sys.stderr,
        )
        for example in a.examples:
            print(f"  {example}", file=sys.stderr)
        return 0
    except (DataError, ValueError, OSError, ZoneInfoNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
