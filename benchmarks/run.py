"""Measure analysis only; report exact benchmark scope alongside measurements."""

import argparse
import json
import platform
import tracemalloc
from datetime import UTC, datetime, timedelta
from time import perf_counter

from spotify_visualiser.analytics import analyse
from spotify_visualiser.models import Audit, Dataset, Play


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=100000)
    args = parser.parse_args()
    if not 1 <= args.events <= 1000000:
        parser.error("--events must be between 1 and 1000000")
    origin = datetime(2024, 1, 1, tzinfo=UTC)
    plays = tuple(
        Play(origin + timedelta(minutes=i * 5), 180000, f"Track {i % 1000}", f"Artist {i % 100}")
        for i in range(args.events)
    )
    dataset = Dataset(plays, Audit(rows=len(plays), accepted=len(plays)))
    tracemalloc.start()
    began = perf_counter()
    report = analyse(dataset)
    elapsed = perf_counter() - began
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert report["summary"]["milliseconds"] == args.events * 180000
    print(
        json.dumps(
            {
                "python": platform.python_version(),
                "events": args.events,
                "analysis_seconds": round(elapsed, 4),
                "analysis_peak_mib": round(peak / 1024**2, 2),
                "scope": "analysis only; input allocation, parsing and rendering excluded",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
