# pi-daily-dashboard

A Raspberry Pi dashboard that displays real-time train departures and weather information on a framebuffer-connected display. Train data is fetched from the [Trafikverket open API](https://api.trafikinfo.trafikverket.se/) and rendered directly to `/dev/fb0`.

## Features

- Real-time SL train departures (southbound and northbound) from a configurable station
- Departure status: on time, delayed (with original time struck through), or cancelled
- Deviation messages for relevant trains
- Current time display
- Weather section (work in progress)
- Resilient rendering — the display keeps updating from cached data during network outages, with a staleness warning shown after 2 minutes

## Project structure

```
main.py         # Orchestrator (work in progress)
train.py        # Fetches and parses train data from Trafikverket, writes JSON cache
renderer.py     # Reads cache files and renders the display image to the framebuffer
weather.py      # Weather data fetching (work in progress)
config.py       # Configuration constants and environment variable loading
utils.py        # Shared utilities across files
```

### Data flow

```
Trafikverket API
      │
  train.py  ──► train_cache.json
                      │
                  train.py  ──► parsed_train_cache.json
                                        │
                                   renderer.py  ──► /dev/fb0
```

The renderer reads only from the parsed cache file, so it can continue rendering during API downtime.

## Requirements

- Python 3.10+
- A Raspberry Pi (or any Linux system) with a framebuffer display at `/dev/fb0`
- The display user must be in the `video` group to write to the framebuffer without root:
  ```bash
  sudo usermod -aG video $USER
  ```

### Python dependencies

```bash
pip install pillow numpy requests python-dotenv
```

The renderer uses the DejaVu font family, which is typically pre-installed on Raspberry Pi OS:
```bash
sudo apt install fonts-dejavu
```

## Configuration

Copy or create a `.env` file in the project root:

```
TRAFIKVERKET_API_KEY=your_api_key_here
```

API keys can be requested for free at [trafikinfo.trafikverket.se](https://api.trafikinfo.trafikverket.se/).

Key constants in [`config.py`](config.py) you may want to adjust:

| Constant | Default | Description |
|---|---|---|
| `TRAIN_STATION_SIGNATURE` | `Upv` | Trafikverket location signature for your station |
| `NORTHBOUND_STATIONS` | `['U', 'Mr', ...]` | Station codes considered northbound endpoints |
| `RELEVANT_TRAIN_COUNT_SOUTH` | `4` | Number of southbound departures to display |
| `RELEVANT_TRAIN_COUNT_NORTH` | `2` | Number of northbound departures to display |
| `TRAIN_SLEEP_DURATION` | `20` | Seconds between train data fetches |
| `MONITOR_RESOLUTION_WIDTH` | `600` | Display width in pixels |
| `MONITOR_RESOLUTION_HEIGHT` | `1024` | Display height in pixels |
| `MONITOR_BPP` | `16` | Framebuffer colour depth (16 or 32) |
| `MONITOR_FB_PATH` | `/dev/fb0` | Path to the framebuffer device |

## Running

```bash
# Fetch and parse train data once (useful for testing)
python train.py

# Render the display once from the current cache
python renderer.py

# Run the full dashboard (orchestrator — work in progress)
python main.py
```

## Cache files

The following files are written to the working directory at runtime and are safe to delete:

| File | Written by | Description |
|---|---|---|
| `train_cache.json` | `train.py` | Raw API response from Trafikverket |
| `parsed_train_cache.json` | `train.py` | Parsed and normalised departure data |
| `train_station_names_cache.json` | `train.py` | Station name lookups to avoid repeated API calls |
| `output.png` | `renderer.py` | Last rendered display image |

## Resources
Weather icons from https://github.com/Makin-Things/weather-icons

## License

See [LICENSE](LICENSE).
