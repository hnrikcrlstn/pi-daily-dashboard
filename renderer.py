import config
import utils
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import json
from dataclasses import dataclass, field
import math
import os
from datetime import datetime, timezone, timedelta

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
    text_color: tuple
    background_color: tuple
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

BG = (0, 0, 0)
FG = (235, 235, 235)
MUTED = (140, 140, 145)
ALERT = (241, 221, 56)
CANCELLED = (200, 60, 60)

STATUS_COLORS = {
    "on_time": FG,
    "delayed": ALERT,
    "cancelled": CANCELLED
}
FONT_DIR = config.FONT_DIR

DEPARTURE_AREA_HEIGHT = 150
DEPARTURE_AREA_BORDER_RADIUS = 20
MONITOR_ROW_HEIGHT = 45
MONITOR_TRANSIT_SECTION_Y_START = 80
MONITOR_MESSAGE_SECTION_Y_START = MONITOR_TRANSIT_SECTION_Y_START + 350
MONITOR_WEATHER_SECTION_Y_START = MONITOR_MESSAGE_SECTION_Y_START + 300
MONITOR_MESSAGE_FONT_HEIGHT = 10
MONITOR_TRANSIT_COLUMS = 3
MONITOR_TRANSIT_ROWS = 2
MONITOR_TRANSIT_RECTANGLE_WIDTH = (config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 4) / MONITOR_TRANSIT_COLUMS - 2 * config.MONITOR_PADDING_X

font_large = load_font(config.FONT_FILENAME_BOLD, 38)
font_medium = load_font(config.FONT_FILENAME_NORMAL, 28)
font_small = load_font(config.FONT_FILENAME_NORMAL, 20)
font_update = load_font(config.FONT_FILENAME_NORMAL, 10)
font_weather = load_font(config.FONT_FILENAME_NORMAL, 15)
font_time = load_font(config.FONT_FILENAME_NORMAL, 64)

def layout_box(index):
    column = index // MONITOR_TRANSIT_ROWS
    row = index % MONITOR_TRANSIT_ROWS
    width = (config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 4) / MONITOR_TRANSIT_COLUMS - 2 * config.MONITOR_PADDING_X
    height = DEPARTURE_AREA_HEIGHT
    x = column * (config.MONITOR_RESOLUTION_WIDTH + config.MONITOR_PADDING_X * 2) / MONITOR_TRANSIT_COLUMS + config.MONITOR_PADDING_X
    y = MONITOR_TRANSIT_SECTION_Y_START + config.MONITOR_PADDING_Y + row * (height + config.MONITOR_PADDING_Y * 2)
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
    combined = list(south[:config.RELEVANT_TRAIN_COUNT_SOUTH]) + list(north[:config.RELEVANT_TRAIN_COUNT_NORTH])
    slots = []
    for i, dep in enumerate(combined):
        status = compute_status(dep)
        slots.append(
            DepartureSlot(
                departure=dep,
                box=layout_box(i),
                status=status,
                background_color=STATUS_COLORS[status],
                text_color=BG,
                time_left=format_time_left(dep),
                advertised_time=dep.get("advertised_arrival_time", "?"),
                scheduled_time=dep.get("new_arrival_time", "?"),
                end_station=dep.get("end_station", {}).get("short_name", "")
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
            if relevant_train_count["north"] >= config.RELEVANT_TRAIN_COUNT_NORTH and relevant_train_count["south"] >= config.RELEVANT_TRAIN_COUNT_SOUTH:
                enough_trains_collected = True
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
            radius=DEPARTURE_AREA_BORDER_RADIUS,
            fill=slot.background_color
        )

        pad = config.MONITOR_PADDING_X // 2
        if slot.status == "delayed":
            draw_strikethrough_text(draw,(slot.box.x + MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad), slot.advertised_time, font=font_small, fill=slot.text_color, anchor="mt")
            draw.text((slot.box.x + MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad + 25), slot.scheduled_time, font=font_large, fill=slot.text_color, anchor="mt")
        elif slot.status == "cancelled":
            # draw.text((slot.box.x + MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad), "Inställd avgång", font=font_small, fill=slot.text_color, anchor="mt")
            draw_strikethrough_text(draw, (slot.box.x + MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad + 25), slot.scheduled_time, font=font_large, fill=slot.text_color, anchor="mt")
            slot.time_left = "Inställt"
        else:
            draw.text((slot.box.x + MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + 2 * pad + 25), slot.scheduled_time, font=font_large, fill=slot.text_color, anchor="mt")
        # draw.text((slot.box.x + config.MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + pad +  50), "Avgång", font=font_small, fill=FG, anchor="mt")
        draw.text((slot.box.x + MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + pad +  80), slot.time_left, font=font_large, fill=slot.text_color, anchor="mt")
        draw.text((slot.box.x + MONITOR_TRANSIT_RECTANGLE_WIDTH / 2, slot.box.y + pad +  120), slot.end_station, font=font_small, fill=slot.text_color, anchor="mt")

    if datetime.now() - fetch_time > timedelta(minutes=2):
        draw.text(
            (config.MONITOR_RESOLUTION_WIDTH / 2, config.MONITOR_RESOLUTION_HEIGHT - config.MONITOR_PADDING_Y),
            f"Tiderna uppdaterades: {fetch_time.strftime('%H:%M')}",
            font=font_update,
            fill=MUTED,
            anchor="mm"
        )

def draw_transit_messages(draw, messages):
    if messages:
        for i, message in enumerate(messages):
            if i < config.MONITOR_MAX_MESSAGE_COUNT:
                draw.text((config.MONITOR_PADDING_X, MONITOR_MESSAGE_SECTION_Y_START + 1.6 * i * MONITOR_MESSAGE_FONT_HEIGHT), message, font=font_weather, fill=FG)
            else:
                draw.text((config.MONITOR_PADDING_X, MONITOR_MESSAGE_SECTION_Y_START + 1.6 * i * MONITOR_MESSAGE_FONT_HEIGHT), "...", font=font_weather, fill=FG)
                return

def draw_weather(draw):
    # Currently only filler for positioning
    # Additional margin-left to monitor message overlap
    draw.rounded_rectangle(
        (3 * config.MONITOR_PADDING_X, MONITOR_WEATHER_SECTION_Y_START, config.MONITOR_RESOLUTION_WIDTH - 2 * config.MONITOR_PADDING_X ,config.MONITOR_RESOLUTION_HEIGHT - config.MONITOR_PADDING_Y - 25),
        radius=DEPARTURE_AREA_BORDER_RADIUS,
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

def main():
    img = Image.new("RGB", (config.MONITOR_RESOLUTION_WIDTH, config.MONITOR_RESOLUTION_HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    #weather_data = utils.load_cache(WEATHER_CACHE)
    transit_data = utils.load_cache(config.TRAIN_PARSED_CACHE_FILENAME)

    #draw_weather_section(draw, weather_data, x=40, y=40)
    draw_transit_section(draw, fetch_relevant_trains(transit_data["data"]),datetime.fromisoformat(transit_data["parsed_at"]),x=40,y=40)
    draw_transit_messages(draw, transit_data.get("deviations", None))
    draw_weather(draw)
    draw_time(draw)

    img.save(config.OUTPUT_IMAGE_FILENAME)
    print(f"Rendered to {config.OUTPUT_IMAGE_FILENAME} at {datetime.now(timezone.utc).isoformat()}")

    push_to_fb()

def push_to_fb():
    img = Image.open(config.OUTPUT_IMAGE_FILENAME).convert("RGB").resize((config.MONITOR_RESOLUTION_WIDTH, config.MONITOR_RESOLUTION_HEIGHT)).rotate(config.MONITOR_IMAGE_ROTATION, expand=True)
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
    main()
