# Engineering decisions

## Boundary normalization

Two Spotify export layouts map to one immutable `Play` value: an aware UTC end timestamp, integer milliseconds, title, artist, and optional URI. JSON values are untrusted at the boundary: booleans are explicitly rejected as durations despite Python's `bool` subclassing `int`. Invalid music rows produce bounded diagnostics; malformed files abort the operation because no reliable row boundary is available.

Raw export fields such as IP address, device identifiers, and location are not carried into the domain model or report. Source paths are not serialized; diagnostic examples use basenames. Reports still contain track and artist names.

Account timestamps have no timezone offset. UTC is an explicit assumption, not recovered location data. A configured IANA timezone controls date filters, daily totals, and hour buckets, including DST transitions. Repeated local hours are combined in the activity matrix; underlying instants remain distinct in session calculations.

## Separate identity policies

Normalized event equality includes timestamp, duration, title, artist, and optional URI. Opt-in deduplication removes only exact equality, with a hash set. It cannot safely infer equivalence between minute-resolution account exports and second-resolution extended exports. Overlapping input paths resolve to unique absolute paths before loading; identical copies at different paths are still separate files unless event deduplication is requested.

Track aggregation uses `(title, artist)` to support both schemas consistently. This fixes same-title collisions across artists but intentionally combines versions or releases with identical metadata. URI-based recording identity would need a separate documented policy and cannot fully identify account-history rows.

## Temporal semantics

Each event contributes its integer duration once to the daily series and activity matrix, assigned to its ending timestamp. This does not split listening across midnight or DST boundaries. Filters select whole events by end date and minimum duration. Filtering happens before sessions are inferred, so excluded events can change inferred session boundaries.

A session is a connected sequence of intervals separated by no more than the chosen idle gap. For each event, infer `[end − duration, end]`, sort by start, and maintain the maximum end encountered. A gap **strictly greater** than the threshold opens a new session. Session listening time sums events; it is not elapsed wall-clock time and overlaps can double-count time. Start/end metadata is serialized in UTC.

Zero-duration events remain play events at the default threshold and contribute to artist play-count diversity and active days. Use `--min-ms 1` to exclude them, or a higher explicit threshold for another analysis. This tool does not implement Spotify's internal definition of a stream.

## Cost model

Let N be accepted events, K unique track/artist groups, D calendar days spanned, and M the largest input file's decoded JSON size.

- File loading: one JSON array at a time, with O(M + N) working memory as normalized records accumulate.
- Sorting: O(N log N) for chronological normalization and interval sessionization.
- Aggregation: O(N); leaderboard sorting O(K log K).
- Daily gap filling: O(D), independent of how many days have plays.
- Storage: O(N + K + D); exact deduplication adds an O(N) hash set.
- The activity matrix always has 168 cells.

The implementation favors an inspectable dependency-free pipeline for personal exports. It is not constant-memory ingestion. An incremental parser and SQLite-backed event store would be sensible extensions if profiling real datasets demonstrates that memory is the limiting factor. Rendering every day in an SVG also grows with D.

## Report contract and verification

JSON includes a schema version, selected parameters, the pre-filter input audit, summary statistics, truncated leaderboards, the full daily series and activity matrix, and inferred sessions. All durations remain integers in milliseconds; presentation converts to hours or minutes. Leaderboard ordering uses duration descending followed by lexical identity. JSON keys are sorted, and no wall-clock generation timestamp is included.

HTML contains no scripts or third-party requests. Export metadata is escaped before interpolation. The seeded demo and randomized invariant test use fixed seeds; the latter checks that track, artist, date, session, and heatmap aggregates conserve the sum of input duration. The CI matrix tests supported interpreter versions, while strict static checking focuses on package code.

Changes from v1 remove artificial UI sleeps, interactive prompts, plotting dependencies, accidental directory-wide assumptions, and the subsampling expression that divided a short history into a zero-length slice step. The compatibility script invokes the new noninteractive CLI; it does not preserve the old internal function API.
