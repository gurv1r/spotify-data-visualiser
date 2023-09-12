import json
from collections import defaultdict
import matplotlib.pyplot as plt
import pyfiglet
import time
from termcolor import colored
import glob

def process_file(filename, song_playtimes, artist_playtimes, daily_playtimes):
    total_ms_played = 0
    with open(filename, 'r', encoding='utf-8') as file:
        data = json.load(file)
        for item in data:
            song_title = item['trackName']
            artist = item['artistName']
            playtime = item['msPlayed']
            end_time = item['endTime'].split(' ')[0]

            song_playtimes[song_title] += playtime
            artist_playtimes[artist] += playtime
            daily_playtimes[end_time] += playtime

            total_ms_played += playtime
    return total_ms_played

def combine_and_calculate_time():
    song_playtimes = defaultdict(int)
    artist_playtimes = defaultdict(int)
    daily_playtimes = defaultdict(int)
    total_ms_played = 0

    for filename in glob.glob('StreamingHistory*.json'):
        total_ms_played += process_file(filename, song_playtimes, artist_playtimes, daily_playtimes)

    total_minutes_played = total_ms_played / (1000 * 60)
    total_hours_played = total_minutes_played / 60
    total_days_played = total_hours_played / 24

    sorted_songs = sorted(song_playtimes.items(), key=lambda x: x[1], reverse=True)
    sorted_artists = sorted(artist_playtimes.items(), key=lambda x: x[1], reverse=True)

    return total_ms_played, total_minutes_played, total_hours_played, total_days_played, sorted_songs, sorted_artists, daily_playtimes

def format_time(ms):
    minutes = ms // (1000 * 60)
    seconds = (ms % (1000 * 60)) / 1000
    return f"{int(minutes)}:{int(seconds)}"

def main():
    welcome_text = pyfiglet.figlet_format('Welcome to Spotify Streaming History!')
    print(colored(welcome_text, 'green'))
    print(colored('Get ready to discover your most played songs, favorite artists, and total listening time!', 'cyan'))
    time.sleep(3)

    ms, minutes, hours, days, sorted_songs, sorted_artists, daily_playtimes = combine_and_calculate_time()

    print(f'\nTotal milliseconds played: {ms}')
    print(f'Total minutes played: {minutes}')
    print(f'Total hours played: {hours}')
    print(f'Total days played: {days}')
    
    print('\nLeaderboard of most played songs:')
    for rank, (song, playtime) in enumerate(sorted_songs[:10], 1):
        formatted_time = format_time(playtime)
        print(colored(f'{rank}. {song} - {formatted_time}', 'blue'))
        if rank <= 3:
            time.sleep(2)

    print('\nFavorite Artists:')
    for rank, (artist, playtime) in enumerate(sorted_artists[:10], 1):
        formatted_time = format_time(playtime)
        print(colored(f'{rank}. {artist} - {formatted_time}', 'blue'))

    # Listening Trends Over Time (plotting)
    dates = list(daily_playtimes.keys())
    playtimes = [playtime / (1000 * 60) for playtime in daily_playtimes.values()]
    plt.plot(dates[::len(dates)//10], playtimes[::len(playtimes)//10]) # Take every nth element to avoid overwhelming x-axis
    plt.xlabel('Date')
    plt.ylabel('Minutes Played')
    plt.title('Listening Trends Over Time')
    plt.show()

    # Prompt user to display all songs
    see_all_songs = input("\nWould you like to see all songs listed by time played? (yes/no): ")
    if see_all_songs.lower() == 'yes':
        print('\nAll songs played:')
        for rank, (song, playtime) in enumerate(sorted_songs, 1):
            formatted_time = format_time(playtime)
            print(f'{rank}. {song} - {formatted_time}')

if __name__ == "__main__":
    main()
