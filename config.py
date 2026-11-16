import os
from dotenv import load_dotenv
load_dotenv()

API_COURTESY_WAIT_SECONDS = 2
REQUESTS_TIMEOUT_DURATION = 15
LOW_INTENSE_START_TIME = "01:00"
LOW_INTENSE_END_TIME = "05:00"
LOW_INTENSE_API_CALLS_FREQUENCY_MINUTES = 10
PROJECT_FOLDER = os.getenv("PROJECT_FOLDER")
if PROJECT_FOLDER is None or type(PROJECT_FOLDER) != str:
    PROJECT_FOLDER = "."

# Trafikverket settings
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_BASE_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
TRAIN_SLEEP_DURATION = 20
RELEVANT_TRAIN_COUNT_SOUTH = 4
RELEVANT_TRAIN_COUNT_NORTH = 2
TRAIN_CACHE_FILENAME = f"{PROJECT_FOLDER}/train_cache.json"
TRAIN_PARSED_CACHE_FILENAME = f"{PROJECT_FOLDER}/parsed_train_cache.json"
TRAIN_STATION_FILENAME = f"{PROJECT_FOLDER}/train_station_names_cache.json"
TRAIN_STATION_MAX_CHARACTERS = 13
TRAIN_TIME_LIMIT_BEFORE = "-0:30:00"
TRAIN_TIME_LIMIT_AFTER = "08:00:00"
TRAIN_STATION_SIGNATURE = "Upv"
TRAIN_API_LIMIT = 150
TRAIN_DEVIATION_HEADER_TEXT = "FÖRSENINGAR"

# Trafikverket API quirks
UNIMPORTANT_MESSAGES = [
        "Resa förbi Arlanda C kräver både UL- och SL- biljett.", 
        "Anslutning till linje 48 mot Gnesta i Södertälje hamn.",
        "Anslutning till linje 48 mot Järna i Södertälje hamn.",
        "Stannar ej vid Trångsund, Skogås, Vega, Jordbro.",
        "Stannar ej vid Arlanda C.",
        "Spårändrat",
        "Stannar även vid Rosersberg.", 
        "Resa förbi Märsta kräver både UL- och SL- biljett.", 
        "Tåget går endast till Södertälje hamn.",
        "Kort tåg"
    ]
NORTHBOUND_STATIONS = ['U', 'Mr', 'Arnc', 'Kn', 'Rs']
SHORT_TRAIN_MARK = "Kort tåg"

# Pillow rendering settings
FONT_DIR = "/usr/share/fonts/google-noto"
FONT_FILENAME_NORMAL = "NotoSansMono-Medium.ttf"
FONT_FILENAME_BOLD = "NotoSansMono-Bold.ttf"
DRAW_IMAGE_UPDATE_FREQUENCY_SECONDS = 8
MONITOR_RESOLUTION_HEIGHT = 1024
MONITOR_RESOLUTION_WIDTH = 600
MONITOR_PADDING_X = 10
MONITOR_PADDING_Y = 10
OUTPUT_IMAGE_FILENAME = f"{PROJECT_FOLDER}/output.png"
MONITOR_BPP = 16
MONITOR_FB_PATH = "/dev/fb0"
MONITOR_MAX_MESSAGE_COUNT = 14
MONITOR_IMAGE_ROTATION = -90

# Weather information
WEATHER_GPS_PRIMARY_LOCATION = "latitude=59.5222&longitude=17.91"
WEATHER_PRIMARY_LOCATION_NAME = "Upplands Väsby"
WEATHER_GPS_SECONDARY_LOCATION = "latitude=59.332257&longitude=18.060147"
WEATHER_SECONDARY_LOCATION_NAME = "Stockholm city"
WEATHER_CACHE_FILENAME = f"{PROJECT_FOLDER}/weather_cache.json"
WEATHER_UPDATE_FREQUENCY_SECONDS = 30 * 60
DAY_NIGHT_BREAKPOINT_END = 21
DAY_NIGHT_BREAKPOINT_START = 6

# News headlines
NEWS_CACHE_FILENAME = f"{PROJECT_FOLDER}/news_cache.json"
NEWS_HEADER_TEXT = "Nyheter"