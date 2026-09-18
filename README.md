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
Trafikverket API          Open-Meteo API
       │                        │
   train.py                 weather.py
   fetch_train_announcements()  fetch_weather()
       │                        │
 train_cache.json        weather_cache.json
       │
   train.py
   parse_trains()
       │
 parsed_train_cache.json  weather_cache.json
              │                  │
              └──────┬───────────┘
                renderer.py
                     │
                  /dev/fb0
```

The renderer reads only from cache files, so it continues rendering during API or network outages. A staleness warning is shown on the display if train data is older than 2 minutes.

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

### Running
`/etc/systemd/system/transit-poll.service`
```bash
[Unit]
Description=Poll transit departures
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/dashboard
ExecStart=/home/pi/dashboard/venv/bin/python /home/pi/dashboard/transit_poll.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/weather-poll.service`
```bash
[Unit]
Description=Fetch weather data
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/dashboard
ExecStart=/home/pi/dashboard/venv/bin/python /home/pi/dashboard/weather_poll.py
```

`/etc/systemd/system/weather-poll.timer`
```bash
[Unit]
Description=Run weather poll hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

`/etc/systemd/system/dashboard-render.service`
```bash
[Unit]
Description=Render dashboard frame and push to framebuffer
After=disable-vtcon.service

[Service]
Type=oneshot
User=pi
WorkingDirectory=/home/pi/dashboard
ExecStart=/home/pi/dashboard/venv/bin/python /home/pi/dashboard/render.py
```

`/etc/systemd/system/dashboard-render.timer`
```bash
[Unit]
Description=Re-render dashboard every 15 seconds

[Timer]
OnBootSec=10s
OnUnitActiveSec=15s

[Install]
WantedBy=timers.target
```

### Activate the services
```bash
sudo systemctl daemon-reload

sudo systemctl enable --now transit-poll.service
sudo systemctl enable --now weather-poll.timer
sudo systemctl enable --now dashboard-render.timer
```
### Verify services
```bash
# confirm all three are active/running
systemctl status transit-poll.service weather-poll.timer dashboard-render.timer

# see when weather/render timers last fired and next will
systemctl list-timers weather-poll.timer dashboard-render.timer

# watch transit's live log
journalctl -u transit-poll.service -f

# confirm a manual weather/render run works before waiting for the timer
sudo systemctl start weather-poll.service
sudo systemctl start dashboard-render.service
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
