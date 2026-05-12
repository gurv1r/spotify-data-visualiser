# spotify-data-visualiser

A small project that reads Spotify Extended Streaming History JSON files and shows your top tracks, artists, and listening duration.

## Improvements included

- Safer JSON parsing (`dict.get`) so malformed rows are skipped gracefully.
- Better time formatting (`mm:ss` with zero-padded seconds).
- Date sorting for trend charts.
- Plotting safety for small datasets (no divide-by-zero slicing issues).
- CLI arguments for flexible usage.

## Usage

1. Place your Spotify files (for example `StreamingHistory0.json`, `StreamingHistory1.json`, etc.) in this directory.
2. Install dependencies:

```bash
pip install matplotlib pyfiglet termcolor
```

3. Run:

```bash
python total.py
```

### Optional flags

```bash
python total.py --top 20 --no-plot
python total.py --pattern "StreamingHistory*.json" --no-banner
```
