"""Compatibility entry point. Prefer `python -m spotify_visualiser`."""

from spotify_visualiser.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
