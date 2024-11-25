from dataclasses import asdict
import json
from datetime import date, datetime
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

from . import config
from .dashboard import generate_dashboard_image, get_dashboard_data, get_image_hash
from .leaf import get_leaf_summary
from .messages import get_message, set_message
from .temperature import get_all_temperature_data, update_temperature_data

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
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
logging.getLogger("azure.monitor.opentelemetry.exporter.export").setLevel(logging.ERROR)
# print(json.dumps([name for name in logging.root.manager.loggerDict])) # handy to list loggers :-)


meter = metrics.get_meter_provider().get_meter("dash-api")
histogram_dashboard_image_requests = meter.create_histogram(
    "dashboard-image-requests", "count", "Number of dashboard image requests"
)


app = FastAPI()


if not config.dashboard_input_dir:
    logger.error("ERROR: DASHBOARD_INPUT_DIR not set")
    sys.exit(1)
if not os.path.isdir(config.dashboard_input_dir):
    logger.error("ERROR: DASHBOARD_INPUT_DIR does not exist")
    sys.exit(1)


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/leaf")
def leaf_summary():
    return get_leaf_summary()


@app.get("/dashboard-image")
def get_dashboard_image(request: Request):

    current_span = trace.get_current_span()
    if (current_span is not None) and (not current_span.is_recording()):
        current_span = None # set to None for simple test later

    action_id  = request.headers.get("action-id")
    if action_id:
        logger.info(f"dashboard-image: Action ID: {action_id}")
        if current_span:
            current_span.set_attribute("action-id", action_id)

    dashboard_data = get_dashboard_data()

    now = datetime.now()
    current_hour = now.hour
    mins_to_sleep = 5
    if current_hour < 6 or current_hour > 22:
        # sleep until 6am
        mins_to_sleep = (6 - current_hour) * 60
        if mins_to_sleep < 0:
            mins_to_sleep += 24 * 60

    logger.debug("dashboard-image: data: ", dashboard_data)

    image_buf = generate_dashboard_image(dashboard_data)
    image_hash = get_image_hash(image_buf)

    logger.info(f"dashboard-image: Mins to sleep: {mins_to_sleep}")
    logger.info(f"dashboard-image: Image hash: {image_hash}")
    if current_span:
        current_span.set_attribute("mins-to-sleep", mins_to_sleep)
        current_span.set_attribute("image-hash", image_hash)

    if "If-None-Match" in request.headers:
        if_none_match_value = request.headers["If-None-Match"]
        logger.info(f"dashboard-image: Got IfNoneMatch: '{if_none_match_value}'")
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
        headers={
            "ETag": str(image_hash),
            "mins-to-sleep": str(mins_to_sleep),
            "actions": json.dumps([a.id for a in dashboard_data.actions]),
        },
    )


@app.get("/messages/{date_value}")
def api_get_message(date_value: str):
    return get_message(date_value=date.fromisoformat(date_value))


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
