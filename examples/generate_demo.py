"""Generate repeatable fictional listening history; never reads personal data."""

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

rng = random.Random(42)
artists = ["Glass Harbour", "Mira Vale", "Night Transit", "Atlas Minor", "Soft Circuit"]
origin = datetime(2024, 1, 1, 8, tzinfo=UTC)
rows = []
for day in range(90):
    if day % 11 == 0:
        continue
    for event in range(rng.randint(8, 28)):
        artist = rng.choices(artists, weights=[4, 3, 2, 1, 1])[0]
        title = f"Movement {rng.randint(1, 5)}"
        rows.append(
            {
                "ts": (
                    origin + timedelta(days=day, minutes=event * 7, hours=10 * (event % 2))
                ).isoformat(),
                "ms_played": rng.randint(30000, 260000),
                "master_metadata_track_name": title,
                "master_metadata_album_artist_name": artist,
                "spotify_track_uri": f"spotify:track:demo-{artists.index(artist)}-{title[-1]}",
            }
        )
output = Path("reports/demo-input.json")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
print(f"Generated {len(rows)} fictional events in {output}")
