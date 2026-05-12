import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict

import glob
import matplotlib.pyplot as plt
import pyfiglet
from termcolor import colored


def process_file(
    filename: str,
    song_playtimes: DefaultDict[str, int],
    artist_playtimes: DefaultDict[str, int],
    daily_playtimes: DefaultDict[str, int],
) -> int:
    total_ms_played = 0
    with open(filename, "r", encoding="utf-8") as file:
        data = json.load(file)

    for item in data:
        song_title = item.get("trackName")
        artist = item.get("artistName")
        playtime = int(item.get("msPlayed", 0))
        end_time = str(item.get("endTime", "")).split(" ")[0]

        if not song_title or not artist or not end_time:
            continue

        song_playtimes[song_title] += playtime
        artist_playtimes[artist] += playtime
        daily_playtimes[end_time] += playtime
        total_ms_played += playtime

    return total_ms_played


def combine_and_calculate_time(pattern: str = "StreamingHistory*.json"):
    song_playtimes: DefaultDict[str, int] = defaultdict(int)
    artist_playtimes: DefaultDict[str, int] = defaultdict(int)
    daily_playtimes: DefaultDict[str, int] = defaultdict(int)
    total_ms_played = 0

    files = sorted(glob.glob(pattern))
    for filename in files:
        total_ms_played += process_file(
            filename,
            song_playtimes,
            artist_playtimes,
            daily_playtimes,
        )

    total_minutes_played = total_ms_played / (1000 * 60)
    total_hours_played = total_minutes_played / 60
    total_days_played = total_hours_played / 24

    sorted_songs = sorted(song_playtimes.items(), key=lambda x: x[1], reverse=True)
    sorted_artists = sorted(artist_playtimes.items(), key=lambda x: x[1], reverse=True)
    sorted_daily_playtimes = dict(sorted(daily_playtimes.items()))

    return (
        files,
        total_ms_played,
        total_minutes_played,
        total_hours_played,
        total_days_played,
        sorted_songs,
        sorted_artists,
        sorted_daily_playtimes,
    )


def format_time(ms: int) -> str:
    minutes = ms // (1000 * 60)
    seconds = (ms % (1000 * 60)) // 1000
    return f"{int(minutes)}:{int(seconds):02d}"


def plot_listening_trends(daily_playtimes: dict[str, int]) -> None:
    if not daily_playtimes:
        print(colored("No daily listening data to plot.", "yellow"))
        return

    dates = list(daily_playtimes.keys())
    playtimes = [playtime / (1000 * 60) for playtime in daily_playtimes.values()]

    step = max(1, len(dates) // 10)
    plt.figure(figsize=(12, 5))
    plt.plot(dates, playtimes)
    plt.xticks(dates[::step], rotation=45, ha="right")
    plt.xlabel("Date")
    plt.ylabel("Minutes Played")
    plt.title("Listening Trends Over Time")
    plt.tight_layout()
    plt.show()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize Spotify extended streaming history."
    )
    parser.add_argument(
        "--pattern",
        default="StreamingHistory*.json",
        help="Glob pattern for Spotify history files.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Number of top songs/artists to display.",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="Disable ASCII-art welcome banner.",
    )
    parser.add_argument(
        "--no-plot",
        action="store_true",
        help="Skip listening trend plot.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.no_banner:
        welcome_text = pyfiglet.figlet_format("Welcome to Spotify Streaming History!")
        print(colored(welcome_text, "green"))
    print(
        colored(
            "Get ready to discover your most played songs, favorite artists, and total listening time!",
            "cyan",
        )
    )

    (
        files,
        ms,
        minutes,
        hours,
        days,
        sorted_songs,
        sorted_artists,
        daily_playtimes,
    ) = combine_and_calculate_time(args.pattern)

    if not files:
        print(
            colored(
                f"No files found with pattern '{args.pattern}' in {Path.cwd()}", "red"
            )
        )
        return

    print(f"\nProcessed {len(files)} files.")
    print(f"Total milliseconds played: {ms}")
    print(f"Total minutes played: {minutes:.2f}")
    print(f"Total hours played: {hours:.2f}")
    print(f"Total days played: {days:.2f}")

    print("\nLeaderboard of most played songs:")
    for rank, (song, playtime) in enumerate(sorted_songs[: args.top], 1):
        print(colored(f"{rank}. {song} - {format_time(playtime)}", "blue"))

    print("\nFavorite Artists:")
    for rank, (artist, playtime) in enumerate(sorted_artists[: args.top], 1):
        print(colored(f"{rank}. {artist} - {format_time(playtime)}", "blue"))

    if not args.no_plot:
        plot_listening_trends(daily_playtimes)

    see_all_songs = input("\nWould you like to see all songs listed by time played? (yes/no): ")
    if see_all_songs.strip().lower() == "yes":
        print("\nAll songs played:")
        for rank, (song, playtime) in enumerate(sorted_songs, 1):
            print(f"{rank}. {song} - {format_time(playtime)}")


if __name__ == "__main__":
    main()
