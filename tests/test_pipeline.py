import contextlib
import io
import json
import math
import random
import tempfile
import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from spotify_visualiser.analytics import analyse
from spotify_visualiser.cli import main
from spotify_visualiser.ingest import DataError, discover, load, normalize
from spotify_visualiser.models import Audit, Dataset, Play
from spotify_visualiser.report import html_report, json_report


def account(**changes):
    return {
        "endTime": "2024-01-01 12:00",
        "msPlayed": 60000,
        "trackName": "Shared title",
        "artistName": "Artist A",
        **changes,
    }


def extended(**changes):
    return {
        "ts": "2024-01-01T12:00:00Z",
        "ms_played": 60000,
        "master_metadata_track_name": "Shared title",
        "master_metadata_album_artist_name": "Artist A",
        **changes,
    }


def dataset(*rows):
    plays = tuple(p for row in rows if (p := normalize(row)) is not None)
    return Dataset(plays, Audit(rows=len(rows), accepted=len(plays)))


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "StreamingHistory0.json"

    def write(self, rows):
        self.path.write_text(json.dumps(rows), encoding="utf-8")
        return self.path

    def test_schemas_have_same_normal_form(self):
        self.assertEqual(normalize(account()), normalize(extended()))

    def test_offset_is_normalized(self):
        self.assertEqual(normalize(extended(ts="2024-01-01T13:00:00+01:00")), normalize(account()))

    def test_reject_invalid_values(self):
        for values in (
            {"msPlayed": -1},
            {"msPlayed": True},
            {"msPlayed": 1.5},
            {"endTime": "yesterday"},
            {"trackName": " "},
            {"artistName": None},
        ):
            with self.subTest(values=values), self.assertRaises(DataError):
                normalize(account(**values))
        with self.assertRaises(DataError):
            normalize([])

    def test_non_music(self):
        self.assertIsNone(normalize(extended(master_metadata_track_name=None)))

    def test_missing_extended_metadata_is_invalid(self):
        with self.assertRaises(DataError):
            normalize({"ts": "2024-01-01T12:00:00Z", "ms_played": 60000})

    def test_unrepresentable_play_interval_is_invalid(self):
        with self.assertRaises(DataError):
            normalize(account(msPlayed=10**100))

    def test_audit_and_deduplication_are_explicit(self):
        self.write(
            [account(), account(), account(msPlayed=-1), extended(master_metadata_track_name=None)]
        )
        result = load([self.path], deduplicate=True)
        self.assertEqual(
            (
                result.audit.rows,
                result.audit.accepted,
                result.audit.invalid,
                result.audit.non_music,
                result.audit.duplicates,
            ),
            (4, 1, 1, 1, 1),
        )
        self.assertEqual(load([self.path]).audit.accepted, 2)
        with self.assertRaisesRegex(DataError, "row 3"):
            load([self.path], strict=True)

    def test_overlapping_input_paths_not_loaded_twice(self):
        self.write([account()])
        self.assertEqual(discover([self.path.parent, self.path]), [self.path.resolve()])

    def test_diagnostics_are_bounded(self):
        self.write([None] * 20)
        audit = load([self.path]).audit
        self.assertEqual(audit.invalid, 20)
        self.assertEqual(len(audit.examples), 5)

    def test_structural_errors_fail_even_in_lenient_mode(self):
        for raw in ("{}", "{invalid", "[NaN]"):
            self.path.write_text(raw)
            if raw == "[NaN]":
                self.assertEqual(load([self.path]).audit.invalid, 1)
            else:
                with self.assertRaises(DataError):
                    load([self.path])

    def test_empty_and_missing_inputs(self):
        with self.assertRaises(DataError):
            load([self.path])
        with self.assertRaises(DataError):
            load([self.path.parent])
        self.write([])
        self.assertEqual(load([self.path]).plays, ())


class AnalyticsTests(unittest.TestCase):
    def test_same_title_different_artists_are_distinct(self):
        r = analyse(dataset(account(), account(artistName="Artist B")))
        self.assertEqual(r["summary"]["unique_tracks"], 2)
        self.assertEqual(r["summary"]["effective_artists"], 2)
        self.assertEqual(r["summary"]["artist_entropy_bits"], 1)
        self.assertEqual(r["summary"]["top_artist_share"], 0.5)

    def test_gap_filling_and_streak(self):
        r = analyse(dataset(*(account(endTime=f"2024-01-{d:02} 12:00") for d in (4, 1, 2))))
        self.assertEqual([d["milliseconds"] for d in r["daily"]], [60000, 60000, 0, 60000])
        self.assertEqual(r["summary"]["longest_streak_days"], 2)
        self.assertEqual(r["summary"]["active_days"], 3)

    def test_timezone_and_inclusive_filter(self):
        d = dataset(extended(ts="2024-01-01T23:30:00Z"), extended(ms_played=10))
        r = analyse(
            d, timezone="Asia/Tokyo", start=date(2024, 1, 2), end=date(2024, 1, 2), min_ms=100
        )
        self.assertEqual(r["summary"]["plays"], 1)
        self.assertEqual(r["weekday_hour_ms"][1][8], 60000)
        self.assertEqual(r["audit"]["accepted"], 2)

    def test_dst_repeated_hour_keeps_both_events(self):
        d = dataset(extended(ts="2024-10-27T00:30:00Z"), extended(ts="2024-10-27T01:30:00Z"))
        self.assertEqual(analyse(d, timezone="Europe/London")["weekday_hour_ms"][6][1], 120000)

    def test_session_gap_is_between_intervals(self):
        d = dataset(
            account(endTime="2024-01-01 12:00"),
            account(endTime="2024-01-01 12:40", msPlayed=35 * 60000),
            account(endTime="2024-01-01 13:11"),
            account(endTime="2024-01-01 14:00"),
        )
        r = analyse(d)
        self.assertEqual([s["plays"] for s in r["sessions"]], [3, 1])

    def test_overlapping_intervals_do_not_shrink_session_end(self):
        d = dataset(
            account(endTime="2024-01-01 12:40", msPlayed=40 * 60000),
            account(endTime="2024-01-01 12:10"),
            account(endTime="2024-01-01 13:05"),
        )
        self.assertEqual(analyse(d)["summary"]["session_count"], 1)

    def test_empty_zero_and_single_day(self):
        for d in (dataset(), dataset(account(msPlayed=0)), dataset(account())):
            r = analyse(d)
            self.assertTrue(math.isfinite(r["summary"]["effective_artists"]))
            self.assertIn("<svg", html_report(r))
            self.assertEqual(json.loads(json_report(r)), r)

    def test_invalid_parameters(self):
        for params in (
            {"top": 0},
            {"min_ms": -1},
            {"session_gap_minutes": -1},
            {"start": date(2024, 2, 1), "end": date(2024, 1, 1)},
        ):
            with self.subTest(params=params), self.assertRaises(ValueError):
                analyse(dataset(), **params)

    def test_randomized_duration_conservation(self):
        rng = random.Random(42)
        origin = datetime(2024, 1, 1, tzinfo=UTC)
        plays = tuple(
            Play(
                origin + timedelta(minutes=rng.randrange(10000)),
                rng.randrange(300000),
                f"Track {i % 7}",
                f"Artist {i % 3}",
            )
            for i in range(500)
        )
        r = analyse(Dataset(plays, Audit()), top=100)
        expected = sum(p.milliseconds for p in plays)
        for values in (r["tracks"], r["artists"], r["daily"], r["sessions"]):
            self.assertEqual(sum(v["milliseconds"] for v in values), expected)
        self.assertEqual(sum(map(sum, r["weekday_hour_ms"])), expected)
        self.assertEqual(r["summary"]["milliseconds"], expected)

    def test_deterministic_ties_and_order(self):
        rows = [account(artistName=a) for a in ("Z", "A")]
        self.assertEqual(
            json_report(analyse(dataset(*rows))), json_report(analyse(dataset(*reversed(rows))))
        )
        self.assertEqual(analyse(dataset(*rows))["artists"][0]["artist"], "A")

    def test_html_escapes_untrusted_metadata(self):
        html = html_report(analyse(dataset(account(trackName='<script>alert("x")</script>'))))
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)


class CliTests(unittest.TestCase):
    def run_cli(self, args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_json_stdout_and_missing_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text(json.dumps([account()]))
            code, out, err = self.run_cli([str(path), "--format", "json"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["summary"]["plays"], 1)
            self.assertIn("Input audit", err)
            self.assertEqual(self.run_cli([str(path.parent / "missing")])[0], 2)

    def test_html_output_and_input_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "StreamingHistory0.json"
            original = json.dumps([account()])
            path.write_text(original)
            output = Path(tmp) / "nested" / "report.html"
            self.assertEqual(
                self.run_cli([str(path), "--format", "html", "--output", str(output)])[0], 0
            )
            self.assertIn("<!doctype html>", output.read_text())
            for source in (path, path.parent):
                self.assertEqual(
                    self.run_cli([str(source), "--format", "json", "--output", str(path)])[0], 2
                )
                self.assertEqual(path.read_text(), original)

    def test_unknown_timezone_and_reversed_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "empty.json"
            path.write_text("[]")
            self.assertEqual(self.run_cli([str(path), "--timezone", "Mars/Olympus"])[0], 2)
            self.assertEqual(
                self.run_cli([str(path), "--start", "2024-02-01", "--end", "2024-01-01"])[0], 2
            )


if __name__ == "__main__":
    unittest.main()
