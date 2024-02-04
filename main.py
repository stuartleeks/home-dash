from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from io import BytesIO
import json
import logging
import os
import sys
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont

app = FastAPI()

from dotenv import load_dotenv

if "SKIP_DOTENV" not in os.environ:
    load_dotenv()

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format="HOME_DASH:%(asctime)s:%(levelname)s: %(message)s",
)

dashboard_input_dir = os.getenv("DASHBOARD_INPUT_DIR")

if not dashboard_input_dir:
    print("ERROR: DASHBOARD_INPUT_DIR not set")
    sys.exit(1)
if not os.path.isdir(dashboard_input_dir):
    print("ERROR: DASHBOARD_INPUT_DIR does not exist")
    sys.exit(1)


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/leaf")
def get_leaf_summary():
    # Get the leaf summary content from leaf-summary.json
    leaf_summary_file = os.path.join(dashboard_input_dir, "leaf-summary.json")

    if not os.path.isfile(leaf_summary_file):
        print("ERROR: leaf-summary.json does not exist")
        sys.exit(1)

    with open(leaf_summary_file) as f:
        leaf_summary = json.load(f)

    return leaf_summary


def hash_data(data):
    if is_dataclass(data):
        data = asdict(data)
    data_string = json.dumps(data)
    data_hash = hash(data_string)
    return data_hash


@dataclass
class LeafData:
    estimated_range: float
    is_plugged_in: bool
    is_charging: bool


@dataclass
class DashboardData:
    leaf: LeafData
    date_string: str = datetime.now().strftime("%A, %d %B %Y")


def get_dashboard_data():
    leaf_summary = get_leaf_summary()

    dashboard_data = DashboardData(
        LeafData(
            estimated_range=leaf_summary["estimated_range"],
            is_plugged_in=leaf_summary["is_connected"],
            is_charging=leaf_summary["charging_status"] != "NOT_CHARGING",
        )
    )

    return dashboard_data


def yes_no(value: bool):
    return "Yes" if value else "No"


@app.get("/dashboard-image")
def get_dashboard_image(request: Request):
    dashboard_data = get_dashboard_data()

    data_hash = hash_data(dashboard_data)
    if "If-None-Match" in request.headers:
        if_none_match_value = request.headers["If-None-Match"]
        print(f"**Got IfNoneMatch: '{if_none_match_value}'", flush=True)
        if request.headers["If-None-Match"] == str(data_hash):
            return Response(status_code=304)

    image = Image.new(mode="RGB", size=(800, 480), color=(255, 255, 255))

    draw = ImageDraw.Draw(image)

    heading_font = ImageFont.load_default(size=25)
    info_main_font = ImageFont.load_default(size=35)
    info_sub_font = ImageFont.load_default(size=25)

    title = "Leeks Dashboard"
    title_width = draw.textlength(title, font=heading_font)
    title_x = (image.width / 2 - title_width) / 2
    draw.text((title_x, 10), title, fill=(0, 0, 0), font=heading_font)

    date_text = dashboard_data.date_string
    date_width = draw.textlength(date_text, font=heading_font)
    date_x = image.width - date_width - 10
    draw.text((date_x, 10), date_text, fill=(0, 0, 0), font=heading_font)

    leaf_range = dashboard_data.leaf.estimated_range
    draw.text(
        (10, 40), f"Range: {leaf_range:.0f} miles", fill=(0, 0, 0), font=info_main_font
    )
    draw.text(
        (10, 80),
        f"Plugged in: {yes_no(dashboard_data.leaf.is_plugged_in)}    Charging: {yes_no(dashboard_data.leaf.is_charging)}",
        fill=(0, 0, 0),
        font=info_sub_font,
    )

    image_buf = BytesIO()
    image.save(image_buf, "JPEG")
    image_buf.seek(0)

    return StreamingResponse(
        image_buf, media_type="image/jpeg", headers={"ETag": str(data_hash)}
    )
