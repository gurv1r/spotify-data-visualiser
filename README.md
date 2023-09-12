
# Spotify Data Visualiser 🎵

`spotify-data-visualiser` is a Python-based tool that brings your Spotify listening habits to life! Delve deep into your extended streaming history to uncover your top tracks, favorite artists, and the total duration you've spent vibing to your jams.

## 🚀 Features

- 🎧 **Top Tracks**: Discover which tracks you've had on repeat.
- 🎤 **Favorite Artists**: Find out which artists have serenaded your ears the most.
- ⏳ **Total Duration**: Visualize the cumulative time you've spent listening to music.
- 📈 **Listening Trends**: See your listening habits plotted over time.

## 📌 Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.x
- Required Python libraries: `json`, `collections`, `matplotlib`, `pyfiglet`, `termcolor`. You can install them using `pip`:
```bash
pip install matplotlib pyfiglet termcolor
```

### 🚀 How to Use

1. **Fetch Your Data**: 
   - Go to Spotify's [Privacy Settings](https://www.spotify.com/account/privacy/).
   - Request your data under 'Download your data'.
   - Once you receive your data, extract the `StreamingHistory*.json` files.

2. **Setup**: 
   - Place the `StreamingHistory*.json` files in the same directory as the `total.py` script.

3. **Run**:
   - Navigate to the directory containing `total.py` in your terminal.
   - Execute the script using:
```bash
python total.py
```
   - Follow the on-screen prompts to view your data.

## 🤝 Contributing

Interested in making this tool even cooler? Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

## 📜 License

This project is licensed under the GNU License.

## 🙌 Acknowledgements

- Spotify, for providing users with their data.
- The open-source community for the essential libraries.
