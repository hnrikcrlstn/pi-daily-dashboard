import config
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import json
from dataclasses import dataclass, field
import math
import os
from datetime import datetime, timezone

@dataclass
class Rectangle:
    x: float
    y: float
    width: float
    height: float

    @property
    def bounds(self):
        return (
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height
        )

@dataclass
class DepartureSlot:
    departure: dict
    box: Rectangle
    status: str
    color: tuple
    time_left: str
    scheduled_time: str
    end_station: str
    advertised_time: str

def load_font(name, size):
    path = os.path.join(FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


# TODO: Move to config file?
BG = (66, 66, 66)
FG = (235, 235, 235)
MUTED = (140, 140, 145)
ALERT = (200, 60, 60)
STATUS_COLORS = {
    "on_time": FG,
    "delayed": ALERT,
    "cancelled": ALERT # Might change to another color in the future
}
FONT_DIR = "/usr/share/fonts/truetype/dejavu"

font_large = load_font("DejaVuSans-Bold.ttf", 40)
font_medium = load_font("DejaVuSans.ttf", 28)
font_small = load_font("DejaVuSans.ttf", 20)
font_weather = load_font("DejaVuSans.ttf", 15)
font_time = load_font("DejaVuSans-Bold.ttf", 64)

def load_cache(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

def layout_box(index):
    column = index // config.MONITOR_TRANSIT_ROWS
    row = index % config.MONITOR_TRANSIT_ROWS
    width = (config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 4) / config.MONITOR_TRANSIT_COLUMS - 2 * config.MONITOR_PADDING_X
    height = config.MONITOR_TRANSIT_RECTANGLE_HEIGHT
    x = column * (config.MONITOR_RESOLUTION_WIDTH + config.MONITOR_PADDING_X * 2) / config.MONITOR_TRANSIT_COLUMS + config.MONITOR_PADDING_X
    y = config.MONITOR_TRANSIT_SECTION_Y_START + config.MONITOR_PADDING_Y + row * (height + config.MONITOR_PADDING_Y * 2)
    return Rectangle(x=x, y=y, width=width, height=height)

def draw_strikethrough_text(draw, xy, text, font, fill, anchor="mm"):
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)
    bbox = draw.textbbox(xy, text, font=font, anchor=anchor)
    left, top, right, bottom = bbox
    mid_y = (top + bottom) / 2
    draw.line((left, mid_y, right, mid_y), fill=fill, width=2)

def compute_status(dep: dict) -> str:
    if dep.get("cancelled",False):
        return "cancelled"
    if dep.get("delayed", False):
        return "delayed"
    return "on_time"

def format_time_left(dep: dict) -> str:
    arrival = datetime.fromisoformat(str(dep["new_arrival_time_timestamp"]))
    delta_min = math.floor(
        (arrival - datetime.now(arrival.tzinfo)).total_seconds() / 60
    )
    return "Nu" if delta_min < 1 else f"{delta_min + 1} min"

def build_slots(south, north):
    combined = list(south[:4]) + list(north[:2])
    slots = []
    for i, dep in enumerate(combined):
        status = compute_status(dep)
        slots.append(
            DepartureSlot(
                departure=dep,
                box=layout_box(i),
                status=status,
                color=STATUS_COLORS[status],
                time_left=format_time_left(dep),
                advertised_time=dep.get("advertised_arrival_time", "?"),
                scheduled_time=dep.get("new_arrival_time", "?"),
                end_station=dep.get("end_station", "").get("short_name", "")
            )
        )
    return slots

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
        arrival_time = datetime.fromisoformat(train["new_arrival_time_timestamp"])
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

    slots = build_slots(
        departures.get("south", []),
        departures.get("north", [])
    )

    for slot in slots:
        draw.rounded_rectangle(
            slot.box.bounds,
            radius=config.MONTIOR_BORDER_RADIUS,
            fill=MUTED
        )

        pad = config.MONITOR_PADDING_X // 2
        if slot.status == "delayed":
            draw_strikethrough_text(draw,(slot.box.x + config.MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad), slot.advertised_time, font=font_small, fill=slot.color, anchor="mt")
            draw.text((slot.box.x + config.MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad + 25), slot.scheduled_time, font=font_large, fill=slot.color, anchor="mt")
        else:
            draw.text((slot.box.x + config.MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad + 25), slot.scheduled_time, font=font_large, fill=slot.color, anchor="mt")
        # draw.text((slot.box.x + config.MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + pad +  50), "Avgång", font=font_small, fill=FG, anchor="mt")
        draw.text((slot.box.x + config.MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + pad +  80), slot.time_left, font=font_large, fill=slot.color, anchor="mt")
        draw.text((slot.box.x + config.MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + pad +  120), slot.end_station, font=font_small, fill=slot.color, anchor="mt")

    if (datetime.now() - fetch_time).total_seconds() > 120:
        draw.text(
            (config.MONITOR_PADDING_X, config.MONITOR_RESOLUTION_HEIGHT - 3 * config.MONITOR_PADDING_Y),
            f"Updated: {fetch_time.strftime('%H:%M')}",
            font=font_small,
            fill=MUTED
        )

def draw_transit_messages(draw, messages):
    if messages:
        for i, message in enumerate(messages):
            if i < config.MONITOR_MAX_MESSAGE_COUNT:
                draw.text((config.MONITOR_PADDING_X, config.MONITOR_MESSAGE_SECTION_Y_START + 1.6 * i * config.MONITOR_MESSAGE_FONT_HEIGHT), message, font=font_weather, fill=FG)
            else:
                draw.text((config.MONITOR_PADDING_X, config.MONITOR_MESSAGE_SECTION_Y_START + 1.6 * i * config.MONITOR_MESSAGE_FONT_HEIGHT), "...", font=font_weather, fill=FG)
                return

def draw_weather(draw):
    # Currently only filler for positioning
    # Additional margin-left to monitor message overlap
    draw.rounded_rectangle(
        (3 * config.MONITOR_PADDING_X, config.MONITOR_WEATHER_SECTION_Y_START, config.MONITOR_RESOLUTION_WIDTH - 2 * config.MONITOR_PADDING_X ,config.MONITOR_RESOLUTION_HEIGHT - config.MONITOR_PADDING_Y),
        radius=config.MONTIOR_BORDER_RADIUS,
        fill=(0,255,0)
    )
def draw_time(draw):
    draw.text(
        (config.MONITOR_RESOLUTION_WIDTH / 2, config.MONITOR_PADDING_Y + 30),
        datetime.strftime(datetime.now(),"%H:%M"),
        font=font_time,
        fill=FG,
        anchor="mm"
    )
""""" - old draw transit section def
def draw_transit_section(draw, departures, fetch_time, x, y):
    if departures is None:
        draw.text((x, y), "Transit unavailable", font=font_medium, fill=MUTED)
        return

    boxes = []
    for i in range(6):
        # 2 rows with 3 colums each for the trains
        row = int(i % 2 == 0)
        column = math.floor(i / 2)
        boxes.append(
            Rectangle(
                x = column * (config.MONITOR_RESOLUTION_WIDTH + config.MONITOR_PADDING_X * 2) / 3 + config.MONITOR_PADDING_X,
                y = config.MONITOR_TRANSIT_RECTANGLE_HEIGHT + row * (config.MONITOR_TRANSIT_RECTANGLE_HEIGHT + config.MONITOR_PADDING_Y * 2),
                width = (config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 4) / 3 - 2 * config.MONITOR_PADDING_X,
                height = config.MONITOR_TRANSIT_RECTANGLE_HEIGHT
            )
        )
    for box in boxes:
        draw.rounded_rectangle(
            box.bounds,
            radius=config.MONTIOR_BORDER_RADIUS,
            fill=FG
        )

    for i, dep in enumerate(departures["south"]):
        time_delta = math.floor((datetime.fromisoformat(str(dep["arrival_timestamp"])) - datetime.now(datetime.fromisoformat(dep["arrival_timestamp"]).tzinfo)).total_seconds()/60)
        time_left = f"{time_delta + 1} min"
        if time_delta < 1:
            time_left = "Nu"
        x_diff = 0
        y_diff = 0
        if i > 1:
            x_diff = 200
            y_diff = -2* config.MONITOR_ROW_HEIGHT
        row_y = y + i * config.MONITOR_ROW_HEIGHT
        is_delayed = dep.get("delayed", False)
        color = ALERT if is_delayed else FG
        line = f"{time_left}\n{dep.get('end_station', {}).get('short_name', '?'):<20}"
        rows = [
            (dep["new_arrival_time"], color, font_large),
            ("Avgång", FG, font_medium),
            (f"{time_left}", color, font_large),
        ]
        draw.text((x + x_diff, row_y + y_diff), line, font=font_small, fill=color)

    if (datetime.now() - fetch_time).total_seconds() > 120:
        draw.text((config.MONITOR_PADDING_X, config.MONITOR_RESOLUTION_HEIGHT - 2 * config.MONITOR_PADDING_Y), f"Updated: {fetch_time.strftime('%H:%M')}", font=font_small, fill=MUTED)
"""

def render():
    img = Image.new("RGB", (config.MONITOR_RESOLUTION_WIDTH, config.MONITOR_RESOLUTION_HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    #weather_data = load_cache(WEATHER_CACHE)
    transit_data = load_cache(config.TRAIN_PARSED_CACHE_FILENAME)

    #draw_weather_section(draw, weather_data, x=40, y=40)
    draw_transit_section(draw, fetch_relevant_trains(transit_data["data"]),datetime.fromisoformat(transit_data["parsed_at"]),x=40,y=40)
    draw_transit_messages(draw, transit_data.get("deviations", None))
    draw_weather(draw)
    draw_time(draw)

    img.save(config.OUTPUT_IMAGET_FILENAME)
    print(f"Rendered to {config.OUTPUT_IMAGET_FILENAME} at {datetime.now(timezone.utc).isoformat()}")

    push_to_fb()

def push_to_fb():
    img = Image.open(config.OUTPUT_IMAGET_FILENAME).convert("RGB").resize((config.MONITOR_RESOLUTION_HEIGHT, config.MONITOR_RESOLUTION_WIDTH)).rotate(-90, expand=True)
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
    with open(config.MONITOR_FB_PATH, "wb") as f:
        f.write(raw)

if __name__ == "__main__":
    render()