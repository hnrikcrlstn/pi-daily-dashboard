import os
from dotenv import load_dotenv

load_dotenv()
TRAFIKVERKET_API_KEY = os.getenv("TRAFIKVERKET_API_KEY")
TRAFIKVERKET_BASE_URL = "https://api.trafikinfo.trafikverket.se/v2/data.json"
TRAIN_SLEEP_DURATION = 20
RELEVANT_TRAIN_COUNT_SOUTH = 4
RELEVANT_TRAIN_COUNT_NORTH = 2
TRAIN_CACHE_FILENAME = "train_cache.json"

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