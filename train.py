import config
import utils
import requests
import logging
from datetime import datetime
import time
import json

def main():
    fetch_train_announcements(requests.Session()) # For testing, manually run fetch outside of loop
    parse_trains()
    #fetch_train_data_loop()

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

    time.sleep(config.API_CURTESY_WAIT_SECONDS)
    try:
        station_data = requests.post(config.TRAFIKVERKET_BASE_URL, headers={'Content-Type': 'application/xml'}, data=xml_request, timeout=(config.TRAIN_SLEEP_DURATION / 2))
        station_data.raise_for_status()

        return {
                "code": station_code,
                "name": station_data.json()["RESPONSE"]["RESULT"][0]["TrainStation"][0]["AdvertisedLocationName"],
                "short_name": station_data.json()["RESPONSE"]["RESULT"][0]["TrainStation"][0]["AdvertisedShortLocationName"]
            }
    except requests.exceptions.RequestException as e:
        logging.error(f"API error from fetch_station_name(): {e}")
    except Exception:
        logging.exception("Unexpected error when fetching station names")

def fetch_train_announcements(trafik_session):
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

        utils.atomic_write(config.TRAIN_CACHE_FILENAME, {
            "fetched_at": f"{datetime.now()}",
            "data": train_data.json()
        })
    except requests.exceptions.RequestException as e:
        logging.error(f"API error from fetch_train_announcements(): {e}")
    except Exception:
        logging.exception("Unexpected error when fetching train announcements")

def confirm_station_names(trains):
    station_dict = {}
    cached_station_names = {}
    new_station_names = []
    for train in trains:
        station_dict[train["ToLocation"][0]["LocationName"]] = True

    cached_station_names = utils.load_cache(config.TRAIN_STATION_FILENAME)
    if cached_station_names is None:
        cached_station_names = {}

    for station in station_dict.keys():
        if station not in cached_station_names:
            new_station_names.append(station)

    for new_station in new_station_names:
        cached_station_names[new_station] = fetch_station_name(new_station)

    if len(new_station_names):
        utils.atomic_write(config.TRAIN_STATION_FILENAME, cached_station_names)
    
    return cached_station_names

def parse_trains():
    TRAIN_NUMBER_INDEX = 1
    cached_response = utils.load_cache(config.TRAIN_CACHE_FILENAME)
    parsed_trains = []
    current_messages = []

    if not cached_response:
        logging.error("No cached response found, exiting loop")
        return
    trains = cached_response['data']['RESPONSE']['RESULT'][0]['TrainAnnouncement']

    station_names = confirm_station_names(trains)

    for train in trains:
        advertised_arrival_time_timestamp = datetime.fromisoformat(str(train["AdvertisedTimeAtLocation"]))
        new_arrival_time_timestamp = advertised_arrival_time_timestamp
        delayed = False
        estimated = train.get("EstimatedTimeAtLocation", train["AdvertisedTimeAtLocation"])
        if train["AdvertisedTimeAtLocation"] != estimated:
            delayed = True
            new_arrival_time_timestamp = datetime.fromisoformat(str(estimated))
        northbound_train = train['ToLocation'][0]['LocationName'] in config.NORTHBOUND_STATIONS
        train_number = train['ProductInformation'][TRAIN_NUMBER_INDEX]['Description']
        if northbound_train:
            train_number += " N"
        else:
            train_number += " S"
        advertised_arrival_time = datetime.strftime(advertised_arrival_time_timestamp, "%H:%M")
        new_arrival_time = datetime.strftime(new_arrival_time_timestamp, "%H:%M")

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
                "advertised_arrival_time_timestamp": str(advertised_arrival_time_timestamp),
                "new_arrival_time_timestamp": str(new_arrival_time_timestamp),
                "advertised_arrival_time": str(advertised_arrival_time),
                "new_arrival_time": str(new_arrival_time),
                "end_station": station_names[train["ToLocation"][0]["LocationName"]],
                "cancelled": train["Canceled"],
                "short_train": short_train,
                "delayed": delayed,
                "deviation": f"{new_arrival_time} Linje {train_number} - {', '.join(current_deviations)}"
            }
        )
        if len(current_deviations):
            current_messages.append(f"{new_arrival_time} Linje {train_number} - {', '.join(current_deviations)}")

    utils.atomic_write(config.TRAIN_PARSED_CACHE_FILENAME, {
        "parsed_at": f"{datetime.now()}",
        "deviations": current_messages,
        "data": parsed_trains
    })

if __name__ == "__main__":
    main()