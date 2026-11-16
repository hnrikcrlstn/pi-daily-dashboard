import time
from datetime import datetime
import logging
import utils
import os
from logging.handlers import TimedRotatingFileHandler
import logging
import requests
import xmltodict
import config

NEWS_FEED_URL = "https://www.svt.se/rss.xml"

def fetch_news():
    try:
        news = requests.get(NEWS_FEED_URL, timeout=config.REQUESTS_TIMEOUT_DURATION)
        news.raise_for_status()

        return xmltodict.parse(news.content)
    except requests.exceptions.RequestException as e:
        logging.error(f"API error from fetch_news(): {e}")
    except Exception:
        logging.exception("Unexpected error when fetching news headlines")

def parse_news():
    news = fetch_news()
    headlines = []
    for headline in news["rss"]["channel"]["item"]:
        headlines.append(headline["title"])

    utils.atomic_write(config.NEWS_CACHE_FILENAME, {
        "parsed_at": f"{datetime.now()}",
        "headlines": headlines
    })

if __name__ == "__main__":
    os.makedirs("logs", exist_ok=True)
    handler = TimedRotatingFileHandler(f"{config.PROJECT_FOLDER}/logs/dashboard-news.log", when="midnight", backupCount=7)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])

    parse_news()