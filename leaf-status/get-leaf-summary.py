#!/usr/bin/env python

import asyncio

import json
import os
import pycarwings3
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


async def run():
    if not output_file:
        logging.error("LEAF_OUTPUT_FILE not set")
        raise Exception("LEAF_OUTPUT_FILE not set")
    
    async def update_battery_status(leaf: pycarwings3.Leaf, wait_interval=1):
        key = await leaf.request_update()
        status = await leaf.get_status_from_update(key)
        counter = 0
        # Currently the nissan servers eventually return status 200 from get_status_from_update(), previously
        # they did not, and it was necessary to check the date returned within get_latest_battery_status().
        while status is None and counter < 10:
            counter += 1
            logging.info(f"Waiting {wait_interval} seconds (counter={counter})...")
            time.sleep(wait_interval)
            status = await leaf.get_status_from_update(key)
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
    async with pycarwings3.Session(username=username, password=password, region=region or "NE") as s:
        logging.info("Logging in...")
        leaf = await s.get_leaf()

        logging.info("Requesting an update from the car...")
        update_status = await update_battery_status(leaf, wait_interval=10)

        leaf_info = await leaf.get_latest_battery_status()
        if leaf_info is None:
            logging.error("Failed to get latest battery status")
            raise Exception("Failed to get latest battery status")
        
        api_update_date = leaf_info.answer["BatteryStatusRecords"]["OperationDateAndTime"]
        update_date = time.strftime("%Y-%m-%d %H:%M:%S")
        logging.debug("api_update_date=", api_update_date)

        driving_analysis = await leaf.get_driving_analysis()
        if driving_analysis is None:
            logging.error("Failed to get driving analysis")
            raise Exception("Failed to get driving analysis")

        electric_mileage = driving_analysis.electric_mileage
        electric_cost_scale = driving_analysis.electric_cost_scale

        miles_per_kWh = get_miles_per_kWh(electric_mileage, electric_cost_scale)

        cruising_range_ac_off_km = leaf_info.cruising_range_ac_off_km
        cruising_range_ac_on_km = leaf_info.cruising_range_ac_on_km
        cruising_range_ac_on_miles = cruising_range_ac_on_km * miles_per_km if cruising_range_ac_on_km else None
        cruising_range_ac_off_miles = cruising_range_ac_off_km * miles_per_km if cruising_range_ac_off_km else None

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




if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        sys.exit(1)
    finally:
        logging.info("Exiting Leaf status script.")
        sys.exit(0)