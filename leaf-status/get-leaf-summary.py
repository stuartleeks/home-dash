#!/usr/bin/env python

import json
import os
import pycarwings2
import time
import logging
import sys

from dotenv import load_dotenv

load_dotenv()

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='LEAF:%(asctime)s:%(levelname)s: %(message)s')

miles_per_km = 0.62137119

username = os.getenv("LEAF_USERNAME")
password = os.getenv("LEAF_PASSWORD")
region = os.getenv("LEAF_REGION")
output_file = os.getenv("LEAF_OUTPUT_FILE")

if not username:
    print("ERROR: LEAF_USERNAME not set")
    sys.exit(1)
if not password:
    print("ERROR: LEAF_PASSWORD not set")
    sys.exit(1)
if not region:
    print("ERROR: LEAF_REGION not set")
    sys.exit(1)
if not output_file:
    print("ERROR: LEAF_OUTPUT_FILE not set")
    sys.exit(1)


def update_battery_status(leaf, wait_interval=1):
    key = leaf.request_update()
    status = leaf.get_status_from_update(key)
    counter = 0
    # Currently the nissan servers eventually return status 200 from get_status_from_update(), previously
    # they did not, and it was necessary to check the date returned within get_latest_battery_status().
    while status is None:
        counter += 1
        logging.info(f"Waiting {wait_interval} seconds (counter={counter})...")
        time.sleep(wait_interval)
        status = leaf.get_status_from_update(key)
        logging.debug(f"status={status}, key={key}")
    return status


def get_miles_per_kWh(electric_mileage, electric_cost_scale):
    electric_mileage = float(electric_mileage)
    if electric_cost_scale == "kWh/mile":
        return 1 / electric_mileage
    if electric_cost_scale == "miles/kWh":
        return electric_mileage
    print(f"ERROR: unknown electric_cost_scale {electric_cost_scale}")
    return None


logging.info("Preparing Session...")
s = pycarwings2.Session(username, password, region)
logging.info("Logging in...")
leaf = s.get_leaf()

logging.info("Requesting an update from the car...")
update_status = update_battery_status(leaf, wait_interval=10)

leaf_info = leaf.get_latest_battery_status()
api_update_date = leaf_info.answer["BatteryStatusRecords"]["OperationDateAndTime"]
update_date = time.strftime("%Y-%m-%d %H:%M:%S")
logging.debug("api_update_date=", api_update_date)

driving_analysis = leaf.get_driving_analysis()

electric_mileage = driving_analysis.electric_mileage
electric_cost_scale = driving_analysis.electric_cost_scale

miles_per_kWh = get_miles_per_kWh(electric_mileage, electric_cost_scale)

cruising_range_ac_off_km = leaf_info.cruising_range_ac_off_km
cruising_range_ac_on_km = leaf_info.cruising_range_ac_on_km
cruising_range_ac_on_miles = cruising_range_ac_on_km * miles_per_km
cruising_range_ac_off_miles = cruising_range_ac_off_km * miles_per_km

battery_capacity = (
    float(leaf_info.battery_capacity) / 10
)  # convert to kWh (e.g. returns 240 for 24 kWh)
battery_remaining_amount = float(leaf_info.battery_remaining_amount) / 10
summary = {
    "update_date": update_date,
    "api_update_date": api_update_date,
    "battery_capacity": battery_capacity,
    "battery_remaining_amount": battery_remaining_amount,
    "charging_status": leaf_info.charging_status,
    "is_connected": leaf_info.is_connected,
    "battery_percent": leaf_info.battery_percent,
    "advice": driving_analysis.advice,
    "electric_mileage": electric_mileage,
    "electric_cost_scale": electric_cost_scale,
    "miles_per_kWh": miles_per_kWh,
    "estimated_range": miles_per_kWh * battery_remaining_amount
    if miles_per_kWh
    else None,
    "cruising_range_ac_off_miles": cruising_range_ac_off_miles,
    "cruising_range_ac_on_miles": cruising_range_ac_on_miles,
}

print(summary)

json.dump(summary, open(output_file, "w"))

