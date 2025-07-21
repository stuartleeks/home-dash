
import asyncio
import logging
import os
import sys
from datetime import datetime
import time
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

import pycarwings3

# Load environment variables
load_dotenv()

logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='LEAF:%(asctime)s:%(levelname)s: %(message)s')

logging.getLogger("pycarwings3").setLevel(logging.DEBUG)
logging.getLogger("pycarwings3.pycarwings3").setLevel(logging.DEBUG)

username = os.getenv("LEAF_USERNAME")
password = os.getenv("LEAF_PASSWORD")
region = os.getenv("LEAF_REGION")
dashboard_input_dir = os.getenv("DASHBOARD_INPUT_DIR")

if not username:
    logging.error("ERROR: LEAF_USERNAME not set")
    sys.exit(1)
if not password:
    logging.error("ERROR: LEAF_PASSWORD not set")
    sys.exit(1)
if not region:
    logging.error("ERROR: LEAF_REGION not set")
    sys.exit(1)
if not dashboard_input_dir:
    logging.error("ERROR: DASHBOARD_INPUT_DIR not set")
    sys.exit(1)


app = FastAPI(title="Leaf API", description="API for Nissan Leaf vehicle data")


def get_leaf_session() -> pycarwings3.Session:
    session = pycarwings3.Session(
        username=username, password=password, region=region or "NE")
    return session


class LeafAdvice(BaseModel):
    title: str
    body: str


class LeafStatus(BaseModel):
    """Model for Leaf vehicle status"""
    update_date: Optional[str] = None
    api_update_date: Optional[str] = None
    battery_capacity: Optional[float] = None
    battery_remaining_amount: Optional[float] = None
    charging_status: Optional[str] = None
    is_connected: Optional[bool] = None
    battery_percent: Optional[float] = None
    advice: Optional[list[LeafAdvice]] = None
    electric_mileage: Optional[float] = None
    electric_cost_scale: Optional[str] = None
    miles_per_kWh: Optional[float] = None
    estimated_range: Optional[float] = None
    cruising_range_ac_off_miles: Optional[float] = None
    cruising_range_ac_on_miles: Optional[float] = None
    is_hvac_running: Optional[bool] = None


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


miles_per_km = 0.62137119


def get_miles_per_kWh(electric_mileage, electric_cost_scale):
    electric_mileage = float(electric_mileage)
    if electric_cost_scale == "kWh/mile":
        return 1 / electric_mileage
    if electric_cost_scale == "miles/kWh":
        return electric_mileage
    print(f"ERROR: unknown electric_cost_scale {electric_cost_scale}")
    return None


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Leaf API is running", "status": "healthy"}


@app.get("/status", response_model=LeafStatus)
async def get_status():
    """Get current Leaf vehicle status"""
    if not dashboard_input_dir:
        logging.error("DASHBOARD_INPUT_DIR not set")
        raise HTTPException(status_code=500, detail="DASHBOARD_INPUT_DIR not set")


    try:
        async with get_leaf_session() as session:
            logging.info("Getting leaf...")
            leaf = await session.get_leaf()

            logging.info("Requesting an update from the car...")
            update_status = await update_battery_status(leaf, wait_interval=10)

            leaf_info = await leaf.get_latest_battery_status()
            if leaf_info is None:
                raise HTTPException(
                    status_code=500, detail="Failed to get latest battery status")
            
            api_update_date = leaf_info.answer["BatteryStatusRecords"]["OperationDateAndTime"]
            update_date = time.strftime("%Y-%m-%d %H:%M:%S")
            logging.debug("api_update_date=", api_update_date)

            driving_analysis = await leaf.get_driving_analysis()
            if driving_analysis is None:
                raise HTTPException(
                    status_code=500, detail="Failed to get driving analysis")

            electric_mileage = driving_analysis.electric_mileage
            electric_cost_scale = driving_analysis.electric_cost_scale

            miles_per_kWh = get_miles_per_kWh(
                electric_mileage, electric_cost_scale)

            hvac_status = await leaf.get_latest_hvac_status()

            cruising_range_ac_off_km = leaf_info.cruising_range_ac_off_km
            cruising_range_ac_on_km = leaf_info.cruising_range_ac_on_km
            cruising_range_ac_on_miles = cruising_range_ac_on_km * miles_per_km if cruising_range_ac_on_km else None
            cruising_range_ac_off_miles = cruising_range_ac_off_km * miles_per_km if cruising_range_ac_off_km else None

            battery_capacity = (
                float(leaf_info.battery_capacity) / 10
            )  # convert to kWh (e.g. returns 240 for 24 kWh)
            battery_remaining_amount = float(
                leaf_info.battery_remaining_amount) / 10

            status = LeafStatus(
                update_date=update_date,
                api_update_date=api_update_date,
                battery_capacity=battery_capacity,
                battery_remaining_amount=battery_remaining_amount,
                charging_status=leaf_info.charging_status,
                is_connected=leaf_info.is_connected,
                battery_percent=leaf_info.battery_percent,
                advice=driving_analysis.advice,
                electric_mileage=electric_mileage,
                electric_cost_scale=electric_cost_scale,
                miles_per_kWh=miles_per_kWh,
                estimated_range=miles_per_kWh * battery_remaining_amount
                if miles_per_kWh
                else None,
                cruising_range_ac_off_miles=cruising_range_ac_off_miles,
                cruising_range_ac_on_miles=cruising_range_ac_on_miles,
                is_hvac_running = hvac_status.is_hvac_running if hvac_status else None,
            )

            status_json = status.model_dump_json(indent=2)
            logging.info(f"Got leaf status successfully {status_json}")
            # Save to file
            output_file = os.path.join(dashboard_input_dir, "leaf-summary.json")
            with open(output_file, "w") as f:
                f.write(status_json)
            logging.info(f"Leaf status saved to {output_file}")

            return status
    except Exception as e:
        logging.error(f"Failed to get leaf status: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get leaf status: {str(e)}")


@app.post("/climate/start")
async def start_climate_control():
    """Start climate control in the Leaf vehicle"""
    try:
        async with get_leaf_session() as session:
            leaf: pycarwings3.Leaf = await session.get_leaf()
            logging.info("Starting climate control...")
            result_key = await leaf.start_climate_control() # TOOO - use key to call check result
            logging.info("Climate control start sent")
            result = await leaf.get_start_climate_control_result(result_key=result_key)
            logging.info(f"Climate control start result: {result}")
            return {"message": "Climate control started"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to start climate control: {str(e)}")


@app.post("/climate/stop")
async def stop_climate_control():
    """Stop climate control in the Leaf vehicle"""
    try:
        async with get_leaf_session() as session:
            leaf: pycarwings3.Leaf = await session.get_leaf()
            logging.info("Stopping climate control...")
            result_key = await leaf.stop_climate_control()
            logging.info("Climate control stop sent")
            
            await asyncio.sleep(10)
            logging.info("Checking climate control stop result...")
            result = await leaf.get_stop_climate_control_result(result_key=result_key)
            logging.info(f"Climate control stop result: {result}")
            return {"message": "Climate control stopped"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to stop climate control: {str(e)}")
