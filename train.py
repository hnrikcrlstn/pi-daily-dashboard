import config
import requests
import os
from datetime import datetime
import time
import json
import logging

def main():
    make_api_call(requests.Session())
    parse_trains()
    #fetch_train_data_loop()

def fetch_train_data_loop():
    SESSION = requests.Session()
    while True:
        make_api_call(SESSION)
        time.sleep(config.TRAIN_SLEEP_DURATION)


def make_api_call(trafik_session):
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
        "<QUERY objecttype='TrainAnnouncement' schemaversion='1.8' orderby='AdvertisedTimeAtLocation' limit='150'>"
        "<FILTER>"
        "<AND>"
        "<EQ name='ActivityType' value='Avgang' />"
        "<EQ name='InformationOwner' value='SL' />"
        "<EQ name='LocationSignature' value='Upv' />"
        "<EQ name='Advertised' value='true' />"
        "<AND>"
        "<GT name='AdvertisedTimeAtLocation' value='$dateadd(-0:30:00)' />"
        "<LT name='AdvertisedTimeAtLocation' value='$dateadd(08:00:00)' />"
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
        train_data = trafik_session.post(config.TRAFIKVERKET_BASE_URL, headers={'Content-Type': 'application/xml'}, data=xml_request, timeout=10)
        train_data.raise_for_status()
        log_point = json.dumps({
            "fetched_at": f"{datetime.now()}",
            "data": train_data.json()
        })
        with open(config.TRAIN_CACHE_FILENAME, 'w') as f:
            json.dump(log_point, f)
    except requests.exceptions.RequestException as e:
        logging.error(f"fan: {e}")
    except Exception:
        logging.exception(Exception)

def parse_trains():
    cached_response = {}
    with open(config.TRAIN_CACHE_FILENAME, 'r') as f:
        cached_response = json.loads(json.load(f))
    trains = cached_response['data']['RESPONSE']['RESULT'][0]['TrainAnnouncement']
    parsed_trains = []
    current_messages = []
    future_relevant_trains = {
        'south': 0,
        'north': 0
    }

    relevant_data_fetched = False
    for train in trains:
        save_current_train = False
        #if train["AdvertisedTimeAtLocation"] > datetime.now(): # fix time check
        northbound_train = train['ToLocation'][0]['LocationName'] in config.NORTHBOUND_STATIONS

        if not relevant_data_fetched:
            relevant_data_fetched = count_relevant_train_data(future_relevant_trains, 'B')
            if northbound_train:
                if not count_relevant_train_data(future_relevant_trains, 'N') and train["ToLocation"][0]["LocationName"] == "U":
                    save_current_train = True
            else:
                if not count_relevant_train_data(future_relevant_trains, 'S'):
                    save_current_train = True
        
        if save_current_train:
            deviation = None
            if "Deviation" in train and train["Deviation"][0]["Description"] not in config.UNIMPORTANT_MESSAGES:
                deviation = str(train["Deviation"][0]["Description"])
            parsed_trains.append({
                "northbound": northbound_train,
                "arrival_date": train["AdvertisedTimeAtLocation"],
                "arrival_time": str(train["AdvertisedTimeAtLocation"]).split("T")[-1].split(".")[0],
                "canceled": train["Canceled"],
                "deviation": deviation

            })
    print(json.dumps(parsed_trains, indent=2))

def count_relevant_train_data(parsed_trains, direction):
    if str(direction).upper() == 'B':
        return bool(parsed_trains['north'] >= config.RELEVANT_TRAIN_COUNT_NORTH and parsed_trains['south'] >= config.RELEVANT_TRAIN_COUNT_SOUTH)
    elif str(direction).upper() == 'N':
        return bool(parsed_trains['north'] >= config.RELEVANT_TRAIN_COUNT_NORTH)
    elif str(direction).upper() == 'S':
        return bool(parsed_trains['south'] >= config.RELEVANT_TRAIN_COUNT_SOUTH)
    else:
        logging.error(f'Unexpected direction value in count_relevant_train_data: {direction}')

if __name__ == "__main__":
    main()