from dataclasses import asdict
import json
from datetime import date, datetime, timedelta, timezone
import logging
import os
import pathlib
import sys
import trace

from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from opentelemetry import metrics, trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.trace import (
    get_tracer_provider,
)

# local import fix
import sys

from pydantic import BaseModel
parent_path = pathlib.Path(__file__).parent
__package__ = parent_path.name
sys.path.append(str(parent_path.absolute().parent))

from .cache import Cache
from .dashboard import generate_dashboard_image, get_dashboard_data, get_image_hash, DashboardData
from .leaf import get_leaf_summary
from .messages import get_message, set_message
from .temperature import get_all_temperature_data, update_temperature_data
from . import config


# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    # level=logging.DEBUG,
    # format="HOME_DASH:%(asctime)s:%(levelname)s: %(message)s",
)
if config.app_insights_connection_string:
    print("Configuring Azure Monitor")
    print(f"Connection string: {config.app_insights_connection_string}")
    configure_azure_monitor(
        connection_string=config.app_insights_connection_string,
    )
else:
    print("No Azure Monitor configuration found")

tracer = trace.get_tracer(__name__,
                          tracer_provider=get_tracer_provider())

logger = logging.getLogger(__name__)

logging.getLogger("azure.core.pipeline.policies").setLevel(logging.ERROR)
logging.getLogger(
    "azure.monitor.opentelemetry.exporter.export").setLevel(logging.ERROR)
# print(json.dumps([name for name in logging.root.manager.loggerDict])) # handy to list loggers :-)


meter = metrics.get_meter_provider().get_meter("dash-api")
histogram_dashboard_image_requests = meter.create_histogram(
    "dashboard-image-requests", "count", "Number of dashboard image requests"
)

if not config.dashboard_input_dir:
    logger.error("ERROR: DASHBOARD_INPUT_DIR not set")
    sys.exit(1)
if not os.path.isdir(config.dashboard_input_dir):
    logger.error("ERROR: DASHBOARD_INPUT_DIR does not exist")
    sys.exit(1)

app = FastAPI()


# We will cache the data here using the ETag header as the cache key
# This allows multiple clients to request data and we can retrieve the
# data from the cache for that request (unless expired) and use that
# to decide whether the current data is sufficiently different to
# generate a new image
data_cache = Cache[DashboardData](ttl=10*60)


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/leaf")
def leaf_summary():
    return get_leaf_summary()


def _reuse_cached_data(cached_data: DashboardData, current_data: DashboardData) -> bool:

    print("cached_data", json.dumps(asdict(cached_data), default=str))
    print("current_data", json.dumps(asdict(current_data), default=str))
    if cached_data is None:
        logger.info("dashboard-image-cache: No cached data")
        return False

    if datetime.now(timezone.utc) - cached_data.generated_date > timedelta(minutes=30):
        # The cached data is too old, so we need to generate a new image
        logger.info("dashboard-image-cache: Cached data is too old")
        return False

    # Update if charge state etc have changed
    if cached_data.leaf.is_charging != current_data.leaf.is_charging:
        logger.info("dashboard-image-cache: Leaf charging state has changed")
        return False
    if cached_data.leaf.is_plugged_in != current_data.leaf.is_plugged_in:
        logger.info("dashboard-image-cache: Leaf plugged in state has changed")
        return False

    if cached_data.leaf.cruising_range_ac_off_miles - current_data.leaf.cruising_range_ac_off_miles > 3:
        logger.info("dashboard-image-cache: Leaf range has changed")
        return False

    # Update if the message has changed
    if cached_data.message != current_data.message:
        logger.info("dashboard-image-cache: Message has changed")
        return False

    if cached_data.pistat0.temperature - current_data.pistat0.temperature > 0.5:
        logger.info("dashboard-image-cache: Temperature has changed")
        return False

    if cached_data.pistat0.humidity - current_data.pistat0.humidity > 2:
        logger.info("dashboard-image-cache: Humidity has changed")
        return False

    logger.info("dashboard-image-cache: Using cached data")
    return True


@app.get("/dashboard-image")
def get_dashboard_image(request: Request):

    current_span = trace.get_current_span()
    if (current_span is not None) and (not current_span.is_recording()):
        current_span = None  # set to None for simple test later

    action_id = request.headers.get("action-id", None)
    if action_id:
        logger.info(f"dashboard-image: Action ID: {action_id}")
        if current_span:
            current_span.set_attribute("action-id", action_id)

    if_none_match_value = request.headers.get("If-None-Match", None)
    if if_none_match_value:
        logger.info(
            f"dashboard-image: Got IfNoneMatch: '{if_none_match_value}'")

    dashboard_data = get_dashboard_data()
    logger.debug("dashboard-image: data: %s", dashboard_data)

    now = datetime.now()
    current_hour = now.hour
    mins_to_sleep = 5
    if current_hour < 6 or current_hour > 22:
        # sleep until 6am
        mins_to_sleep = (6 - current_hour) * 60
        if mins_to_sleep < 0:
            mins_to_sleep += 24 * 60
    logger.info(f"dashboard-image: Mins to sleep: {mins_to_sleep}")
    if current_span:
        current_span.set_attribute("mins-to-sleep", mins_to_sleep)

    if not action_id and if_none_match_value:
        # Don't cache if we have an action id
        # or if the caller didn't send an If-None-Match header (i.e. they're not trying to cache)

        # Get the cached data
        cached_data = data_cache.get(if_none_match_value)
        if cached_data:
            logger.info(
                f"dashboard-image: Got cached data for {if_none_match_value}")
            if _reuse_cached_data(cached_data, dashboard_data):
                histogram_dashboard_image_requests.record(
                    1, {"status": "304",
                        "user-agent": request.headers.get("User-Agent")}
                )
                return Response(
                    status_code=304, headers={"mins-to-sleep": str(mins_to_sleep)}
                )

    image_buf = generate_dashboard_image(dashboard_data)
    image_hash = get_image_hash(image_buf)
    logger.info(f"dashboard-image: Image hash: {image_hash}")
    if current_span:
        current_span.set_attribute("image-hash", image_hash)

    data_cache.set(str(image_hash), dashboard_data)

    histogram_dashboard_image_requests.record(
        1, {"status": "200", "user-agent": request.headers.get("User-Agent")}
    )
    return StreamingResponse(
        image_buf,
        media_type="image/jpeg",
        headers={
            "ETag": str(image_hash),
            "mins-to-sleep": str(mins_to_sleep),
            "actions": json.dumps([a.id for a in dashboard_data.actions]),
        },
    )


@app.get("/messages/{date_value}")
def api_get_message(date_value: str):
    try:
        date_value = date.fromisoformat(date_value)
    except ValueError:
        return Response(status_code=400, content="Invalid date format")

    message = get_message(date_value=date_value)
    if message is None:
        return Response(status_code=404, content="No message found")
    return {"message": message}


class MessageSetRequest(BaseModel):
    message: str


@app.put("/messages/{date_value}")
def api_set_message(date_value: str, data: MessageSetRequest):
    set_message(date.fromisoformat(date_value), data.message)
    return {"status": "ok"}


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


# https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html
FastAPIInstrumentor.instrument_app(
    app=app,
    http_capture_headers_server_request="action-id",
    http_capture_headers_server_response="actions,mins-to-sleep",
)
