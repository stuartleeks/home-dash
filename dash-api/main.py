from datetime import datetime
import logging
import os
import pathlib
import sys

from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from opentelemetry import metrics

# local import fix
import sys

from pydantic import BaseModel
parent_path = pathlib.Path(__file__).parent
__package__ = parent_path.name
sys.path.append(str(parent_path.absolute().parent))

from . import config
from .leaf import get_leaf_summary
from .dashboard import generate_dashboard_image, get_dashboard_data, get_image_hash
from .temperature import get_all_temperature_data, update_temperature_data

app = FastAPI()

if config.app_insights_connection_string:
    print("Configuring Azure Monitor")
    print(f"Connection string: {config.app_insights_connection_string}")
    configure_azure_monitor(
        connection_string=config.app_insights_connection_string,
    )
else:
    print("No Azure Monitor configuration found")

meter = metrics.get_meter_provider().get_meter("dash-api")
histogram_dashboard_image_requests = meter.create_histogram(
    "dashboard-image-requests", "count", "Number of dashboard image requests"
)

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="HOME_DASH:%(asctime)s:%(levelname)s: %(message)s",
)


if not config.dashboard_input_dir:
    print("ERROR: DASHBOARD_INPUT_DIR not set")
    sys.exit(1)
if not os.path.isdir(config.dashboard_input_dir):
    print("ERROR: DASHBOARD_INPUT_DIR does not exist")
    sys.exit(1)


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/leaf")
def leaf_summary():
    return get_leaf_summary()


@app.get("/dashboard-image")
def get_dashboard_image(request: Request):
    dashboard_data = get_dashboard_data()

    now = datetime.now()
    current_hour = now.hour
    mins_to_sleep = 5
    if current_hour < 6 or current_hour > 22:
        # sleep until 6am
        mins_to_sleep = (6 - current_hour) * 60
        if mins_to_sleep < 0:
            mins_to_sleep += 24 * 60

    print("**Dashboard data: ", dashboard_data, flush=True)

    image_buf = generate_dashboard_image(dashboard_data)
    image_hash = get_image_hash(image_buf)

    print(f"    Mins to sleep: {mins_to_sleep}", flush=True)
    print(f"    Image hash: {image_hash}", flush=True)

    if "If-None-Match" in request.headers:
        if_none_match_value = request.headers["If-None-Match"]
        print(f"    Got IfNoneMatch: '{if_none_match_value}'", flush=True)
        if request.headers["If-None-Match"] == str(image_hash):
            histogram_dashboard_image_requests.record(
                1, {"status": "304",
                    "user-agent": request.headers.get("User-Agent")}
            )
            return Response(
                status_code=304, headers={"mins-to-sleep": str(mins_to_sleep)}
            )

    histogram_dashboard_image_requests.record(
        1, {"status": "200", "user-agent": request.headers.get("User-Agent")}
    )
    return StreamingResponse(
        image_buf,
        media_type="image/jpeg",
        headers={"ETag": str(image_hash), "mins-to-sleep": str(mins_to_sleep)},
    )

@app.get("/temperature/{id}")
def get_temperature(id: str):
    t = get_all_temperature_data()
    if t is None:
        return None
    return t.get(id, None)


class TemeratureUpdateRequest(BaseModel):
    temperature: float
    humidity: float

@app.put("/temperature/{id}")
def update_temperature(id: str, data: TemeratureUpdateRequest):
    update_temperature_data(id, data.temperature, data.humidity)
    return {"status": "ok"}