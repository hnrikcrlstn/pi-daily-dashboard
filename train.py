import config
import requests
import os
import tempfile
from datetime import datetime
import time
import json
import logging

def main():
    fetch_train_announcements(requests.Session())
    parse_trains()
    #fetch_train_data_loop()

def atomic_write(path, data):
    dir_ = os.path.dirname(path) or '.'
    fd, tmp_path = tempfile.mkstemp(dir=dir_)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    os.replace(tmp_path, path)

def fetch_train_data_loop():
    SESSION = requests.Session()
    while True:
        fetch_train_announcements(SESSION)
        parse_trains()
        time.sleep(config.TRAIN_SLEEP_DURATION)

def fetch_station_name(station_code):
    xml_request = (
        "<REQUEST>"
        f"<LOGIN authenticationkey='{config.TRAFIKVERKET_API_KEY}'/>"
        "<QUERY objecttype='TrainStation' schemaversion='1.0'>"
        "<FILTER>"
        f"<EQ name='LocationSignature' value='{station_code}'/>"
        "</FILTER>"
        "</QUERY>"
        "</REQUEST>"
    )

    time.sleep(1)
    try:
        station_data = requests.post(config.TRAFIKVERKET_BASE_URL, headers={'Content-Type': 'application/xml'}, data=xml_request, timeout=(config.TRAIN_SLEEP_DURATION / 2))
        station_data.raise_for_status()

        return {
                "code": station_code,
                "name": station_data.json()["RESPONSE"]["RESULT"][0]["TrainStation"][0]["AdvertisedLocationName"],
                "short_name": station_data.json()["RESPONSE"]["RESULT"][0]["TrainStation"][0]["AdvertisedShortLocationName"]
            }
    except requests.exceptions.RequestException as e:
        logging.error(f"fan: {e}")
    except Exception:
        logging.exception(Exception)

def fetch_train_announcements(trafik_session):
    log_filename = f"logs/run_{datetime.now().strftime('%Y-%m-%d')}.log"
    os.makedirs('logs', exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler()
        ]
    )

    xml_request = (
        "<REQUEST>"
        f"<LOGIN authenticationkey='{config.TRAFIKVERKET_API_KEY}'/>"
        f"<QUERY objecttype='TrainAnnouncement' schemaversion='1.8' orderby='AdvertisedTimeAtLocation' limit='{config.TRAIN_API_LIMIT}'>"
        "<FILTER>"
        "<AND>"
        "<EQ name='ActivityType' value='Avgang' />"
        "<EQ name='InformationOwner' value='SL' />"
        f"<EQ name='LocationSignature' value='{config.TRAIN_STATION_SIGNATURE}' />"
        "<EQ name='Advertised' value='true' />"
        "<AND>"
        f"<GT name='AdvertisedTimeAtLocation' value='$dateadd({config.TRAIN_TIME_LIMIT_BEFORE})' />"
        f"<LT name='AdvertisedTimeAtLocation' value='$dateadd({config.TRAIN_TIME_LIMIT_AFTER})' />"
        "</AND>"
        "</AND>"
        "</FILTER>"
        "<INCLUDE>ProductInformation</INCLUDE>"
        "<INCLUDE>EstimatedTimeAtLocation</INCLUDE>"
        "<INCLUDE>TimeAtLocation</INCLUDE>"
        "<INCLUDE>AdvertisedTimeAtLocation</INCLUDE>"
        "<INCLUDE>ToLocation</INCLUDE>"
        "<INCLUDE>OtherInformation</INCLUDE>"
        "<INCLUDE>Canceled</INCLUDE>"
        "<INCLUDE>Deviation</INCLUDE>"
        "</QUERY>"
        "</REQUEST>"
    )

    try:
        train_data = trafik_session.post(config.TRAFIKVERKET_BASE_URL, headers={'Content-Type': 'application/xml'}, data=xml_request, timeout=(config.TRAIN_SLEEP_DURATION / 2))
        train_data.raise_for_status()

        atomic_write(config.TRAIN_CACHE_FILENAME, {
            "fetched_at": f"{datetime.now()}",
            "data": train_data.json()
        })
    except requests.exceptions.RequestException as e:
        logging.error(f"fan: {e}")
    except Exception:
        logging.exception(Exception)

def confirm_station_names(trains):
    station_dict = {}
    cached_station_names = {}
    new_station_names = []
    for train in trains:
        station_dict[train["ToLocation"][0]["LocationName"]] = True

    if os.path.isfile(config.TRAIN_STATION_FILENAME):
        with open(config.TRAIN_STATION_FILENAME, 'r') as f:
            cached_station_names = json.load(f)
    else:

        with open(config.TRAIN_STATION_FILENAME, 'w') as f:
            json.dump({}, f)

    for station in station_dict.keys():
        if station not in cached_station_names:
            new_station_names.append(station)

    for new_station in new_station_names:
        cached_station_names[new_station] = fetch_station_name(new_station)

    if len(new_station_names):
        atomic_write(config.TRAIN_STATION_FILENAME, cached_station_names)
    
    return cached_station_names

def parse_trains():
    cached_response = {}
    parsed_trains = []
    current_messages = []

    with open(config.TRAIN_CACHE_FILENAME, 'r') as f:
        cached_response = json.load(f)
    if cached_response == {}:
        logging.error("No cached response found, exiting loop")
    trains = cached_response['data']['RESPONSE']['RESULT'][0]['TrainAnnouncement']

    station_names = confirm_station_names(trains)

    for train in trains:
        arrival_time = datetime.fromisoformat(str(train["AdvertisedTimeAtLocation"]))
        now = datetime.now(arrival_time.tzinfo)
        time_delta = arrival_time - now
        northbound_train = train['ToLocation'][0]['LocationName'] in config.NORTHBOUND_STATIONS

        current_deviations = []
        short_train = False
        if "Deviation" in train:
            for deviation in train["Deviation"]:
                if deviation["Description"] not in config.UNIMPORTANT_MESSAGES:
                    current_deviations.append(str(deviation["Description"]))
                if deviation["Description"] in config.SHORT_TRAIN_MARK:
                    short_train = True
        parsed_trains.append(
            {
                "northbound": northbound_train,
                "arrival_date": train["AdvertisedTimeAtLocation"].split('T')[0],
                "time_delta_seconds": time_delta.total_seconds(),
                "arrival_time": str(datetime.time(arrival_time)),
                "end_station": station_names[train["ToLocation"][0]["LocationName"]],
                "canceled": train["Canceled"],
                "short_train": short_train,
                "deviation": current_deviations
            }
        )
        if "Deviation" in train and train["Deviation"][0]["Description"] not in config.UNIMPORTANT_MESSAGES:
            current_messages.append(str(train["Deviation"][0]["Description"]))

    atomic_write(config.TRAIN_PARSED_CACHE_FILENAME, {
        "parsed_at": f"{datetime.now()}",
        "deviations": current_messages,
        "data": parsed_trains
    })

if __name__ == "__main__":
    main()