import config
import utils
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from functools import lru_cache
from dataclasses import dataclass
import math
import os
from datetime import datetime, timedelta
import time

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
    box: Rectangle
    status: str
    text_color: tuple
    background_color: tuple
    time_left: str
    scheduled_time: str
    end_station: str
    advertised_time: str
    short_train: boolnn
    delay_correction_y: int

@lru_cache(maxsize=None)
def load_icon(icon):
    path = os.path.join(ICON_DIR, f"{icon}.png")
    icon = Image.open(path).convert("RGBA")
    if icon.size != (ICON_SIZE, ICON_SIZE):
        icon = icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
    return icon

def load_font(name, size):
    path = os.path.join(FONT_DIR, name)
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size)

BG = (0, 0, 0)
FG = (235, 235, 235)
MUTED = (140, 140, 145)
ALERT = (241, 221, 56)
CANCELLED = (200, 60, 60)

STATUS_COLORS_BACKGROUND = {
    "on_time": BG,
    "delayed": ALERT,
    "cancelled": CANCELLED
}

STATUS_COLORS_TEXT = {
    "on_time": FG,
    "delayed": BG,
    "cancelled": BG
}

FONT_DIR = config.FONT_DIR
ICON_DIR = "icons"
ICON_SIZE = 80

DEPARTURE_AREA_HEIGHT = 150
DEPARTURE_AREA_BORDER_RADIUS = 20
TRANSIT_SECTION_HEIGHT = 340
MESSAGE_AREA_HEIGHT = 290
MESSAGE_HEADLINES_GAP = 5
TRANSIT_SECTION_Y_START = 70
DEPARTURE_DELAY_CORRECTION_Y = -17
TRAIN_CUTOFF_TIME = -60
MESSAGE_SECTION_Y_START = TRANSIT_SECTION_Y_START + TRANSIT_SECTION_HEIGHT
WEATHER_SECTION_Y_START = MESSAGE_SECTION_Y_START + MESSAGE_AREA_HEIGHT
WEATHER_ICON_CENTER_OFFSET = 55
TRANSIT_COLUMNS = 3
TRANSIT_ROWS = 2
TRANSIT_CELL_WIDTH = int((config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 4) / TRANSIT_COLUMNS - 2 * config.MONITOR_PADDING_X)
WEATHER_CELL_WIDTH = 195
MAX_WIDTH = int(config.MONITOR_RESOLUTION_WIDTH - 2 * config.MONITOR_PADDING_X)

font_header_large = load_font(config.FONT_FILENAME_NORMAL, 64)
font_header_small = load_font(config.FONT_FILENAME_NORMAL, 28)
font_subheader = load_font(config.FONT_FILENAME_BOLD, 20)
font_time_left = load_font(config.FONT_FILENAME_BOLD, 40)
font_departure_time = load_font(config.FONT_FILENAME_BOLD, 30)
font_small = load_font(config.FONT_FILENAME_NORMAL, 20)
font_extrasmall = load_font(config.FONT_FILENAME_NORMAL, 12)
font_normal = load_font(config.FONT_FILENAME_NORMAL, 15)
font_footer = load_font(config.FONT_FILENAME_NORMAL, 10)

def layout_box(index):
    column = index // TRANSIT_ROWS
    row = index % TRANSIT_ROWS
    width = (config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X * 4) / TRANSIT_COLUMNS - 2 * config.MONITOR_PADDING_X
    height = DEPARTURE_AREA_HEIGHT
    x = column * (config.MONITOR_RESOLUTION_WIDTH + config.MONITOR_PADDING_X * 2) / TRANSIT_COLUMNS + config.MONITOR_PADDING_X
    y = TRANSIT_SECTION_Y_START + config.MONITOR_PADDING_Y + row * (height + config.MONITOR_PADDING_Y * 2)
    return Rectangle(x=x, y=y, width=width, height=height)

def draw_strikethrough_text(draw, xy, text, font, fill, anchor="mm"):
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)
    bbox = draw.textbbox(xy, text, font=font, anchor=anchor)
    left, top, right, bottom = bbox
    mid_y = (top + bottom) / 2
    draw.line((left, mid_y, right, mid_y), fill=fill, width=2)

def draw_rotated_text(img, text, font, fill, x, y, angle=90):
    # Measure the text first so the temp canvas is only as big as it needs to be
    dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    # Draw the text horizontally onto its own transparent layer
    text_layer = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
    ImageDraw.Draw(text_layer).text((-bbox[0], -bbox[1]), text, font=font, fill=fill)

    # Rotate the layer — expand=True keeps corners from clipping
    rotated = text_layer.rotate(angle, expand=True)

    img.paste(rotated, (x, y), mask=rotated)

def compute_status(dep: dict) -> str:
    if dep.get("cancelled",False):
        return "cancelled"
    if dep.get("delayed", False):
        return "delayed"
    return "on_time"

def format_time_left(dep: dict) -> str:
    arrival = datetime.fromisoformat(str(dep["new_arrival_time_timestamp"]))
    delta_minutes = math.floor(
        (arrival - datetime.now(arrival.tzinfo)).total_seconds() / 60
    )
    return "Nu" if delta_minutes < 0 else f"{delta_minutes + 1} min"

def build_transit_slots(south, north):
    combined = list(south[:config.RELEVANT_TRAIN_COUNT_SOUTH]) + list(north[:config.RELEVANT_TRAIN_COUNT_NORTH])
    slots = []
    for i, dep in enumerate(combined):
        status = compute_status(dep)
        slots.append(
            DepartureSlot(
                box=layout_box(i),
                status=status,
                background_color=STATUS_COLORS_BACKGROUND[status],
                text_color=STATUS_COLORS_TEXT[status],
                time_left=format_time_left(dep),
                advertised_time=dep.get("advertised_arrival_time", "?"),
                scheduled_time=dep.get("new_arrival_time", "?"),
                end_station=dep.get("end_station", {}).get("short_name", ""),
                short_train=dep.get("short_train", False),
                delay_correction_y= DEPARTURE_DELAY_CORRECTION_Y if status == "delayed" else 0
            )
        )
    return slots

def filter_relevant_trains(trains):
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

        if not enough_trains_collected and time_delta.total_seconds() > TRAIN_CUTOFF_TIME:
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

def draw_transit_section(draw, departures, fetch_time):
    if departures is None:
        draw.text((config.MONITOR_RESOLUTION_WIDTH / 2, TRANSIT_SECTION_Y_START + 3 * config.MONITOR_PADDING_Y), "Transit unavailable", font=font_time_left, fill=MUTED)
        return

    slots = build_transit_slots(
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
        if slot.status == "cancelled":
            draw_strikethrough_text(draw, (slot.box.x + TRANSIT_CELL_WIDTH / 2, slot.box.y + 2 * pad + 25), slot.scheduled_time, font=font_time_left, fill=slot.text_color, anchor="mt")
            slot.time_left = ""
            slot.scheduled_time = "Inställt"
        elif slot.status == "delayed":
            draw_strikethrough_text(draw,(slot.box.x + TRANSIT_CELL_WIDTH / 2, slot.box.y + 10 * pad), slot.advertised_time, font=font_small, fill=slot.text_color, anchor="mt")
        draw.text((slot.box.x + TRANSIT_CELL_WIDTH / 2, slot.box.y + 2 * pad + 15 + slot.delay_correction_y), slot.time_left, font=font_time_left, fill=slot.text_color, anchor="mt")
        draw.text((slot.box.x + TRANSIT_CELL_WIDTH / 2, slot.box.y + pad +  70 + 0.25 * slot.delay_correction_y), slot.scheduled_time, font=font_departure_time, fill=slot.text_color, anchor="mt")
        draw.text((slot.box.x + TRANSIT_CELL_WIDTH / 2, slot.box.y + pad +  110 + 0.5 * slot.delay_correction_y), slot.end_station[:config.TRAIN_STATION_MAX_CHARACTERS], font=font_small, fill=slot.text_color, anchor="mt")
        if slot.short_train:
            draw.text((slot.box.x + TRANSIT_CELL_WIDTH / 2, slot.box.y + pad + 130), "Kort tåg", font=font_extrasmall, fill=BG, anchor="mt")
    if datetime.now() - fetch_time > timedelta(minutes=2):
        draw.text(
            (config.MONITOR_RESOLUTION_WIDTH / 2, config.MONITOR_RESOLUTION_HEIGHT - config.MONITOR_PADDING_Y),
            f"Tågtiderna uppdaterades: {fetch_time.strftime('%H:%M')}",
            font=font_footer,
            fill=MUTED,
            anchor="mm"
        )

def draw_transit_messages(draw, messages):
    if messages:
        for i, message in enumerate(messages):
            if i < config.MONITOR_MAX_MESSAGE_COUNT:
                draw.text((config.MONITOR_PADDING_X, MESSAGE_SECTION_Y_START + 1.6 * i * font_normal.size), message, font=font_normal, fill=FG)
            else:
                draw.text((config.MONITOR_PADDING_X, MESSAGE_SECTION_Y_START + 1.6 * i * font_normal.size), "...", font=font_normal, fill=FG)
                return

def draw_headlines(draw, headlines):
    if headlines:
        draw.text((config.MONITOR_PADDING_X, MESSAGE_SECTION_Y_START), config.NEWS_HEADER_TEXT, font=font_subheader, fill=FG)
        y = MESSAGE_SECTION_Y_START + font_subheader.size
        for headline in headlines:
            lines = wordwrap_text(draw, headline, font_normal)
            block_height = len(lines) * font_normal.size + font_subheader.size
            print(y)
            if y + block_height > WEATHER_SECTION_Y_START - font_normal.size:
                break
            for line in lines:
                draw.text((config.MONITOR_PADDING_X, y), line, font=font_normal, fill=FG)
                y += font_normal.size
            y += MESSAGE_HEADLINES_GAP

def wordwrap_text(draw, text, font=font_normal):
    if text:
        printable_lines = []
        current_line = ""
        for word in text.split():
            lenght_test = f"{current_line} {word}".strip()
            if draw.textlength(lenght_test, font=font) <= MAX_WIDTH:
                current_line = lenght_test
            else:
                if current_line:
                    printable_lines.append(current_line)
                current_line = word
        if current_line:
            printable_lines.append(current_line)
        return printable_lines

def draw_weather(draw, img, weather_data):
    if weather_data is None:
        draw.text((config.MONITOR_RESOLUTION_WIDTH / 2, WEATHER_SECTION_Y_START), "Fel när vädret läses in", font=font_small, fill=FG, anchor="mt")
        return


    locations = [
        (config.WEATHER_PRIMARY_LOCATION_NAME, weather_data["primary_weather"], 0),
        (config.WEATHER_SECONDARY_LOCATION_NAME, weather_data["secondary_weather"], 150)
    ]
    offsets = [("Nu", "now"), ("Om 3h", "3h"), ("Om 9h", "9h")]

    for n, (location_label, location_data, start_y) in enumerate(locations):
        # Draw location headers
        draw_rotated_text(img, location_label, font_extrasmall, FG, config.MONITOR_PADDING_X, WEATHER_SECTION_Y_START + start_y, 90)
        for i, (time_label, key) in enumerate(offsets):
            draw_weather_entry(draw, img, location_data[key], int(i * WEATHER_CELL_WIDTH + config.MONITOR_PADDING_X), start_y)
            # Draw time headers only once
            if n == 0:
                draw.text((int(i * WEATHER_CELL_WIDTH  + TRANSIT_CELL_WIDTH / 2 + config.MONITOR_PADDING_X), WEATHER_SECTION_Y_START - 20), time_label ,font=font_extrasmall, fill=FG, anchor="mm")

def draw_weather_entry(draw, img, entry, x, y_offset):
    day_or_night_icon = "day_icon" if datetime.now().hour < config.DAY_NIGHT_BREAKPOINT_END and datetime.now().hour > config.DAY_NIGHT_BREAKPOINT_START else "night_icon" 
    icon_file = entry["weather"][day_or_night_icon]
    icon = load_icon(os.path.splitext(icon_file)[0])
    img.paste(icon, (x + WEATHER_ICON_CENTER_OFFSET, WEATHER_SECTION_Y_START + y_offset), mask=icon)

    text_x = x + WEATHER_CELL_WIDTH / 2
    draw.text((text_x, y_offset + WEATHER_SECTION_Y_START + ICON_SIZE + 5), f"{entry['temperature']} °C", font=font_normal, fill=FG, anchor="mt")
    draw.text((text_x, y_offset + WEATHER_SECTION_Y_START + ICON_SIZE + 25), entry['weather']['name'], font=font_normal, fill=FG, anchor="mt")
    draw.text((text_x, y_offset + WEATHER_SECTION_Y_START + ICON_SIZE + 45), f"{entry["wind_speed"]} m/s", font=font_normal, fill=FG, anchor="mt")

def draw_time(draw):
    now = datetime.now()
    draw.text(
        (config.MONITOR_RESOLUTION_WIDTH / 2, config.MONITOR_PADDING_Y + 30),
        datetime.strftime(now,"%H:%M"),
        font=font_header_large,
        fill=FG,
        anchor="mm"
    )
    draw.text(
        (config.MONITOR_PADDING_X, config.MONITOR_PADDING_Y + 30),
        datetime.strftime(now, "Vecka %-U"),
        font= font_header_small,
        fill=FG,
        anchor="lm"
    )
    draw.text(
        (config.MONITOR_RESOLUTION_WIDTH - config.MONITOR_PADDING_X, config.MONITOR_PADDING_Y + 30),
        datetime.strftime(now, "%-d/%-m"),
        font= font_header_small,
        fill=FG,
        anchor="rm"
    )

def main():
    img = Image.new("RGB", (config.MONITOR_RESOLUTION_WIDTH, config.MONITOR_RESOLUTION_HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    weather_data = utils.load_cache(config.WEATHER_CACHE_FILENAME)
    transit_data = utils.load_cache(config.TRAIN_PARSED_CACHE_FILENAME)
    messages = transit_data.get("deviations", [])

    draw_time(draw)
    if transit_data:
        draw_transit_section(draw, filter_relevant_trains(transit_data.get("data", {})),datetime.fromisoformat(transit_data.get("parsed_at", str(datetime.fromtimestamp(1)))))
        if len(messages) == 0:
            draw_headlines(draw, utils.load_cache(config.NEWS_CACHE_FILENAME)["headlines"])
        else:
            draw_transit_messages(draw, messages)
    if weather_data:
        draw_weather(draw, img, weather_data)

    img.save(config.OUTPUT_IMAGE_FILENAME)

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
    while True:
        main()
        time.sleep(config.DRAW_IMAGE_UPDATE_FREQUENCY_SECONDS)
