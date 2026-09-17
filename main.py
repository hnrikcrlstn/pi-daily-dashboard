import time
import datetime
import train
import weather
import renderer
from logging.handlers import TimedRotatingFileHandler
import logging
import os

os.makedirs("logs", exist_ok=True)
handler = TimedRotatingFileHandler("logs/dashboard.log", when="midnight", backupCount=7)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

logging.basicConfig(level=logging.INFO, handlers=[handler, logging.StreamHandler()])

if __name__ == "__main__":
    
    train.main()
    weather.main()
    renderer.main()

    # Schedule
    # Train updates - every 20s
    # Weather - every 30 min