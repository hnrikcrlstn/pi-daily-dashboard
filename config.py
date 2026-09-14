import os
from dotenv import load_dotenv

load_dotenv()
# Trafikverket settings
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_BASE_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
TRAIN_SLEEP_DURATION = 20
RELEVANT_TRAIN_COUNT_SOUTH = 4
RELEVANT_TRAIN_COUNT_NORTH = 2
TRAIN_CACHE_FILENAME = "train_cache.json"
TRAIN_PARSED_CACHE_FILENAME = "parsed_train_cache.json"
TRAIN_STATION_FILENAME = "train_station_names_cache.json"
TRAIN_TIME_LIMIT_BEFORE = "-0:30:00"
TRAIN_TIME_LIMIT_AFTER = "08:00:00"
TRAIN_STATION_SIGNATURE = "Upv"
TRAIN_API_LIMIT = 150

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
        "Kort tåg",
        "Anslutning till linje 48 mot Gnesta i Södertälje hamn."
    ]
NORTHBOUND_STATIONS = ['U', 'Mr', 'Arnc', 'Kn', 'Rs']
SHORT_TRAIN_MARK = "Kort tåg"

# Pillow rendering settings
MONITOR_RESOLUTION_HEIGHT = 1024
MONITOR_RESOLUTION_WIDTH = 600
MONITOR_PADDING_X = 10
MONITOR_PADDING_Y = 10
OUTPUT_IMAGET_FILENAME = "output.png"
MONITOR_TRANSIT_RECTANGLE_HEIGHT = 150
MONITOR_TRANSIT_RECTANGLE_MARGIN = 10
MONTIOR_BORDER_RADIUS = 20
MONITOR_BPP = 16
MONITOR_FBT_PATH = "/dev/fb0"