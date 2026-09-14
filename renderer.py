import config
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import json
from dataclasses import dataclass
import math
import os
from datetime import datetime, timezone

# For testing purposes - enable on actual hardware
RENDER_IMAGE = False

@dataclass
class Rectangle:
    x: int
    y: int
    width: int
    height: int

    @property
    def bounds(self):
        return (
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height
        )

def load_font(name, size):
    path = os.path.join(FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

BG = (66, 66, 66)
FG = (235, 235, 235)
MUTED = (140, 140, 145)
ALERT = (200, 60, 60)
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

font_large = load_font("DejaVuSans-Bold.ttf", 48)
font_medium = load_font("DejaVuSans.ttf", 28)
font_small = load_font("DejaVuSans.ttf", 20)

def load_cache(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

def fetch_relevant_trains(trains):
    relevant_train_count = {
        'south': 0,
        'north': 0
    }
    relevant_train_data = {
        "south": [],
        "north": []
    }
    enough_trains_collected = False
    for train in trains:
        arrival_time = datetime.fromisoformat(train["arrival_timestamp"])
        now = datetime.now(arrival_time.tzinfo)
        time_delta = arrival_time - now

        if not enough_trains_collected and time_delta.total_seconds() > 0:
            if train["northbound"]:
                if relevant_train_count["north"] < config.RELEVANT_TRAIN_COUNT_NORTH and train["end_station"]["code"] == "U":
                    relevant_train_count["north"] += 1
                    relevant_train_data["north"].append(train)
            elif relevant_train_count["south"] < config.RELEVANT_TRAIN_COUNT_SOUTH:
                relevant_train_count["south"] += 1
                relevant_train_data["south"].append(train)
    return relevant_train_data

def draw_transit_section(draw, departures, fetch_time, x, y):
    if departures is None:
        draw.text((x, y), "Transit unavailable", font=font_medium, fill=MUTED)
        return

    boxes = []
    for i in range(6):
        top_row = int(i % 2 == 0)
        boxes.append(
            Rectangle(
                x=math.floor(i/2) * (config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 2) / 3 + config.MONITOR_PADDING_X,
                y=config.MONITOR_TRANSIT_RECTANGLE_HEIGHT + top_row * (config.MONITOR_TRANSIT_RECTANGLE_HEIGHT + config.MONITOR_PADDING_Y * 2),
                width=(config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 2) / 3 - config.MONITOR_PADDING_X,
                height=config.MONITOR_TRANSIT_RECTANGLE_HEIGHT
            )
        )
    for box in boxes:
        draw.rounded_rectangle(
            box.bounds,
            radius=config.MONTIOR_BORDER_RADIUS,
            fill=FG
        )

    row_height = 45
    for i, dep in enumerate(departures["south"]):
        time_delta = math.floor((datetime.fromisoformat(str(dep["arrival_timestamp"])) - datetime.now(datetime.fromisoformat(dep["arrival_timestamp"]).tzinfo)).total_seconds()/60)
        time_left = f"{time_delta + 1} min"
        if time_delta < 1:
            time_left = "Nu"
        x_diff = 0
        y_diff = 0
        if i > 1:
            x_diff = 200
            y_diff = -2*row_height
        row_y = y + i * row_height
        is_delayed = dep.get("delayed", True)
        color = ALERT if is_delayed else FG
        line = f"{time_left}\n{dep.get('end_station', {}).get('short_name', '?'):<20}"
        rows = [
            (dep["new_arrival_time"], color, font_large),
            ("Avgång", FG, font_medium),
            (f"{time_left}", color, font_large),
        ]
        draw.text((x + x_diff, row_y + y_diff), line, font=font_small, fill=color)

    #fetched_at = data.get("fetched_at")
    if fetch_time:
        age_note = f"Updated {fetch_time}"
        draw.text((x, y + 6 * row_height + 10), age_note, font=font_small, fill=MUTED)

def render():
    img = Image.new("RGB", (config.MONITOR_RESOLUTION_WIDTH, config.MONITOR_RESOLUTION_HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    #weather_data = load_cache(WEATHER_CACHE)
    transit_data = load_cache(config.TRAIN_PARSED_CACHE_FILENAME)

    #draw_weather_section(draw, weather_data, x=40, y=40)
    draw_transit_section(draw, fetch_relevant_trains(transit_data["data"]),transit_data["parsed_at"],x=40,y=40)

    img.save(config.OUTPUT_IMAGET_FILENAME)
    print(f"Rendered to {config.OUTPUT_IMAGET_FILENAME} at {datetime.now(timezone.utc).isoformat()}")

    if RENDER_IMAGE:
        push_to_fb()


def push_to_fb():
    img = Image.open(config.OUTPUT_IMAGET_FILENAME).convert("RGB").resize((config.MONITOR_RESOLUTION_WIDTH, config.MONITOR_RESOLUTION_HEIGHT))
    arr = np.array(img)

    if config.MONITOR_BPP == 16:
        # Pack to RGB565
        r = (arr[:, :, 0] >> 3).astype(np.uint16)
        g = (arr[:, :, 1] >> 2).astype(np.uint16)
        b = (arr[:, :, 2] >> 3).astype(np.uint16)
        rgb565 = (r << 11) | (g << 5) | b
        raw = rgb565.astype("<u2").tobytes()
    elif config.MONITOR_BPP == 32:
        rgba = np.dstack([arr, np.full(arr.shape[:2], 255, dtype=np.uint8)])
        raw = rgba.tobytes()
    else:
        raise ValueError(f"Unsupported bpp: {config.MONITOR_BPP}")
    with open(config.MONITOR_FBT_PATH, "wb") as f:
        f.write(raw)

if __name__ == "__main__":
    render()