import requests
import json
import config
import time
from datetime import datetime
import logging
import utils

WEATHER_SESSION = requests.session()
WEATHER_API_BASE_URL = "https://api.open-meteo.com/v1/forecast"
WEATHER_API_PARAMS = "hourly=temperature_2m,weathercode,windspeed_10m&daily=weathercode,temperature_2m_max,temperature_2m_min,windspeed_10m_max&current_weather=true&windspeed_unit=ms&forecast_days=2&timezone=Europe%2FBerlin"
WEATHER_TIME_INDEX_3H_DELAY = 3
WEATHER_TIME_INDEX_9H_DELAY = 9

def parse_weather_codes(code):
    # Translate WMO weather codes to names and matching icons
    match(code):
        case 0:
            return {
                "name": "Molnfritt",
                "day_icon": "clear-day.png",
                "night_icon": "clear-night.png"
            }
        case 1:
            return {
                "name": "Lätt molnigt",
                "day_icon": "cloudy-1-day.png",
                "night_icon": "cloudy-1-night.png"
            }
        case 2:
            return {
                "name": "Molnigt",
                "day_icon": "cloudy-2-day.png",
                "night_icon": "cloudy-2-night.png"
            }
        case 3:
            return {
                "name": "Kraftigt molnigt",
                "day_icon": "cloudy-3-day.png",
                "night_icon": "cloudy-3-night.png"
            }
        case 45:
            return {
                "name": "Dimma",
                "day_icon": "haze-day.png",
                "night_icon": "haze-night.png"
            }
        case 48:
            return {
                "name": "Isdimma",
                "day_icon": "fog-day.png",
                "night_icon": "fog-night.png"
            }
        case 51:
            return {
                "name": "Lätt duggregn",
                "day_icon": "rainy-1-day.png",
                "night_icon": "rainy-1-night.png"
            }
        case 53:
            return {
                "name": "Duggregn",
                "day_icon": "rain-and-sleet-mix.png",
                "night_icon": "rain-and-sleet-mix.png"
            }
        case 55:
            return {
                "name": "Kraftigt duggregn",
                "day_icon": "rainy-1-day.png",
                "night_icon": "rainy-1-night.png"
            }
        case 56:
            return {
                "name": "Underkylt regn",
                "day_icon": "rainy-1-day.png",
                "night_icon": "rainy-1-night.png"
            }
        case 57:
            return {
                "name": "Underkylt regn",
                "day_icon": "rainy-1-day.png",
                "night_icon": "rainy-1-night.png"
            }
        case 61:
            return {
                "name": "Lätt regn",
                "day_icon": "rainy-2-day.png",
                "night_icon": "rainy-3-night.png"
            }
        case 63:
            return {
                "name": "Regn",
                "day_icon": "rain-2-day.png",
                "night_icon": "rain-2-night.png"
            }
        case 65:
            return {
                "name": "Kraftigt regn",
                "day_icon": "rain-3-day.png",
                "night_icon": "rain-3-night.png"
            }
        case 66:
            return {
                "name": "Snöblandat regn",
                "day_icon": "snow-and-sleet-mix.png",
                "night_icon": "snow-and-sleet-mix.png"
            }
        case 67:
            return {
                "name": "Kraftigt snöblandat regn",
                "day_icon": "rain-and-snow-mix.png",
                "night_icon": "rain-and-snow-mix.png"
            }
        case 71:
            return {
                "name": "Lätt snö",
                "day_icon": "snowy-1-day.png",
                "night_icon": "snowy-1-night.png"
            }
        case 73:
            return {
                "name": "Snö",
                "day_icon": "snowy-2-day.png",
                "night_icon": "snowy-2-night.png"
            }
        case 75:
            return {
                "name": "Kraftig snö",
                "day_icon": "snowy-3-day.png",
                "night_icon": "snowy-3-night.png"
            }
        case 77:
            return {
                "name": "Hagel",
                "day_icon": "hail.png",
                "night_icon": "hail.png"
            }
        case 80:
            return {
                "name": "Spidda skurar",
                "day_icon": "rain-1-day.png",
                "night_icon": "rain-2-night.png"
            }
        case 81:
            return {
                "name": "Skurar",
                "day_icon": "rain-2-day.png",
                "night_icon": "rain-2-night.png"
            }
        case 82:
            return {
                "name": "Kraftiga skurar",
                "day_icon": "rain-3-day.png",
                "night_icon": "rain-3-night.png"
            }
        case 85:
            return {
                "name": "Snöskurar",
                "day_icon": "snowy-1-day.png",
                "night_icon": "snowy-1-night.png"
            }
        case 86:
            return {
                "name": "Kraftiga snöskurar",
                "day_icon": "snowy-3-day.png",
                "night_icon": "snowy-3-night.png"
            }
        case 95:
            return {
                "name": "Åska",
                "day_icon": "thunderstorms.png",
                "night_icon": "thunderstorms.png"
            }
        case 96:
            return {
                "name": "Åska med hagel",
                "day_icon": "thunderstorms.png",
                "night_icon": "thunderstorms.png"
            }
        case 99:
            return {
                "name": "Åska, mycket hagel",
                "day_icon": "thunderstorms.png",
                "night_icon": "thunderstorms.png"
            }
        case None:
            return {
                "name": "Väderkod hittades inte",
                "day_icon": "tornado.png",
                "night_icon": "tornado.png"
            }
    return None

def main():
    primary_location_weather = parse_weather(
        fetch_weather(config.WEATHER_GPS_PRIMARY_LOCATION)
    )
    time.sleep(config.API_CURTESY_WAIT_SECONDS)
    secondary_location_weather = parse_weather(
        fetch_weather(config.WEATHER_GPS_SECONDARY_LOCATION)
    )
    now = datetime.now()

    utils.atomic_write(config.WEATHER_CACHE_FILENAME, {
        "parsed_at": str(now),
        "primary_weather": primary_location_weather,
        "secondary_weather": secondary_location_weather
    })


def fetch_weather(location):
    try:
        weather = WEATHER_SESSION.get(f"{WEATHER_API_BASE_URL}?{location}&{WEATHER_API_PARAMS}", headers={"Accept": "application/json"}, timeout=20)
        weather.raise_for_status()
        return weather.json()
    except requests.exceptions.RequestException as e:
        logging.error(f"API error from fetch_weather(): {e}")
    except Exception:
        logging.exception(Exception)

def parse_weather(weather):
    if not weather:
        return None

    now = datetime.now()

    index_3_hours = now.hour + WEATHER_TIME_INDEX_3H_DELAY
    index_9_hours = now.hour + WEATHER_TIME_INDEX_9H_DELAY

    parsed_weather = {
        "now": {
            "weather": parse_weather_codes(weather.get("current_weather", {}).get("weathercode", None)),
            "temperature": weather.get("current_weather", {}).get("temperature"),
            "wind_speed": weather.get("current_weather", {}).get("windspeed", 0)
        },
        "3h": {
            "weather": parse_weather_codes(weather.get("hourly", {}).get("weathercode", [])[index_3_hours]),
            "temperature": weather.get("hourly", {}).get("temperature_2m", [])[index_3_hours],
            "hours": weather.get("hourly", {}).get("time")[index_3_hours],
            "wind_speed": weather.get("hourly", {}).get("windspeed_10m", [])[index_3_hours]
        },
        "9h": {
            "weather": parse_weather_codes(weather.get("hourly", {}).get("weathercode", [])[index_9_hours]),
            "temperature": weather.get("hourly", {}).get("temperature_2m", [])[index_9_hours],
            "hours": weather.get("hourly", {}).get("time")[index_9_hours],
            "wind_speed": weather.get("hourly", {}).get("windspeed_10m", [])[index_9_hours]
        }
    }

    return parsed_weather

if __name__ == "__main__":
    main()