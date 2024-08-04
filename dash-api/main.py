import hashlib
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from io import BytesIO
import itertools
import json
import logging
import os
import sys

from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from opentelemetry import metrics
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

app = FastAPI()

from dotenv import load_dotenv

if "SKIP_DOTENV" not in os.environ:
    load_dotenv()

app_insights_connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
if app_insights_connection_string:
    print("Configuring Azure Monitor")
    print(f"Connection string: {app_insights_connection_string}")
    configure_azure_monitor(
        connection_string=app_insights_connection_string,
    )
else:
    print("No Azure Monitor configuration found")

meter = metrics.get_meter_provider().get_meter("dash-api")
histogram_dashboard_image_requests = meter.create_histogram(
    "dashboard-image-requests", "count", "Number of dashboard image requests"
)

script_dir = os.path.dirname(os.path.abspath(__file__))
leaf_image_dir = os.path.join(script_dir, "leaf_images")

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


messages_file = os.getenv("MESSAGES_FILE") or os.path.join(
    dashboard_input_dir, "messages.json"
)
print(f"Using messages file: {messages_file}")


@app.get("/")
def root():
    return {"message": "Hello World"}


@app.get("/leaf")
def get_leaf_summary():
    # Get the leaf summary content from leaf-summary.json
    leaf_summary_file = os.path.join(dashboard_input_dir, "leaf-summary.json")

    if not os.path.isfile(leaf_summary_file):
        print("ERROR: leaf-summary.json does not exist")
        sys.exit(1)  # TODO - handle this gracefully!

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
class WeatherData:
    time: str
    description: str
    temperature: float
    feels_like: float
    icon_path: str
    wind_speed_mph: float
    wind_gust_mph: float | None


def get_weather():
    # Get the leaf summary content from leaf-summary.json
    weather_summary_file = os.path.join(dashboard_input_dir, "weather-summary.json")

    if not os.path.isfile(weather_summary_file):
        print("ERROR: weather-summary.json does not exist")
        return None

    with open(weather_summary_file) as f:
        weather_summary_json = json.load(f)
        # parse the json into a list of WeatherData objects
        weather_data = []
        for weather in weather_summary_json["forecast"]:
            weather_data.append(WeatherData(**weather))

    return weather_data


def get_message():
    if os.path.isfile(messages_file):
        with open(messages_file) as f:
            messages = json.load(f)

        date_string = datetime.now().strftime("%Y-%m-%d")
        if date_string in messages:
            return messages[date_string]
        else:
            print("No message for ", date_string, flush=True)
            return ""
    else:
        print("No messages file: ", messages_file, flush=True)
        return ""


@dataclass
class LeafData:
    is_plugged_in: bool
    is_charging: bool
    cruising_range_ac_off_miles: float
    cruising_range_ac_on_miles: float
    icon_path: str


LEAF_ICON_NOT_PLUGGED_IN = "not_plugged_in.png"
LEAF_ICON_PLUGGED_IN = "plugged_in.png"
LEAF_ICON_CHARGING = "charging.png"


@dataclass
class DashboardData:
    leaf: LeafData
    date_string: str
    message: str
    weather: list[WeatherData] | None


def get_leaf_icon(plugged_in: bool, charging: bool):
    if plugged_in:
        if charging:
            return LEAF_ICON_CHARGING
        return LEAF_ICON_PLUGGED_IN
    return LEAF_ICON_NOT_PLUGGED_IN


def get_rounded_weather_data(weather_data: WeatherData) -> WeatherData:
    return WeatherData(
        time=weather_data.time,
        description=weather_data.description,
        temperature=round(weather_data.temperature),
        feels_like=round(weather_data.feels_like),
        icon_path=weather_data.icon_path,
        wind_speed_mph=round(weather_data.wind_speed_mph),
        wind_gust_mph=round(weather_data.wind_gust_mph) if weather_data.wind_gust_mph else None,
    )

def get_dashboard_data():
    leaf_summary = get_leaf_summary()

    plugged_in = leaf_summary["is_connected"]
    charging = leaf_summary["charging_status"] != "NOT_CHARGING"
    leaf_icon = get_leaf_icon(plugged_in, charging)
    weather = get_weather()
    if weather:
        # take up to three weather entries
        weather = list(itertools.islice(weather, 3))
        weather = [get_rounded_weather_data(w) for w in weather]

    dashboard_data = DashboardData(
        leaf=LeafData(
            cruising_range_ac_off_miles=leaf_summary["cruising_range_ac_off_miles"],
            cruising_range_ac_on_miles=leaf_summary["cruising_range_ac_on_miles"],
            is_plugged_in=plugged_in,
            is_charging=charging,
            icon_path=os.path.join(leaf_image_dir, leaf_icon),
        ),
        date_string=datetime.now().strftime("%A, %d %B %Y"),
        message=get_message(),
        weather=weather,
    )

    return dashboard_data


def yes_no(value: bool):
    return "Yes" if value else "No"


def pure_pil_alpha_to_color_v2(image, color=(255, 255, 255)):
    """Alpha composite an RGBA Image with a specified color.

    Simpler, faster version than the solutions above.

    Source: http://stackoverflow.com/a/9459208/284318

    Keyword Arguments:
    image -- PIL RGBA Image object
    color -- Tuple r, g, b (default 255, 255, 255)

    """
    # from: https://stackoverflow.com/questions/9166400/convert-rgba-png-to-rgb-with-pil
    image.load()  # needed for split()
    background = Image.new("RGB", image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background


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

    print("Dashboard data: ", dashboard_data, flush=True)

    image_buf = generate_dashboard_image(dashboard_data)
    image_hash = get_image_hash(image_buf)

    print(f"**Image hash: {image_hash}", flush=True)

    if "If-None-Match" in request.headers:
        if_none_match_value = request.headers["If-None-Match"]
        print(f"**Got IfNoneMatch: '{if_none_match_value}'", flush=True)
        if request.headers["If-None-Match"] == str(image_hash):
            histogram_dashboard_image_requests.record(
                1, {"status": "304", "user-agent": request.headers.get("User-Agent")}
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

def get_image_hash(image_buf):
    hash_md5 = hashlib.md5()
    hash_md5.update(image_buf.getvalue())
    image_hash = hash_md5.hexdigest()
    return image_hash

def generate_dashboard_image(dashboard_data):
    image = Image.new(mode="RGBA", size=(800, 480), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    message_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 25)

    draw_heading(image, draw, dashboard_data)

    draw_leaf_info(image, draw, dashboard_data.leaf)

    draw_weather(image, draw, dashboard_data.weather, weather_left=30, weather_top=150)

    # draw lines for buttons
    for x in [80, 240, 400, 560, 720]:
        draw.line((x, 460, x, 490), fill=(0, 0, 0))

    message_font_size = 25
    message = dashboard_data.message
    while message_font_size > 10:
        message_font = ImageFont.truetype(
            "fonts/FiraCode-Regular.ttf", message_font_size
        )
        message_width = draw.textlength(message, font=message_font)
        if message_width < image.width - 20:
            message_x = (image.width - message_width) / 2
            draw.text((message_x, 400), message, fill=(0, 0, 0), font=message_font)
            break
        message_font_size -= 1

    # handle the alpha channel (needed for PNGs from OpenWeatherMap)
    image = pure_pil_alpha_to_color_v2(image)

    image_buf = BytesIO()
    image.save(image_buf, "JPEG")
    image_buf.seek(0)
    return image_buf


def draw_centred(draw, xy, text, font):
    """Draw text centred on the x coordinate.
    Returns the width of the text drawn."""
    x = xy[0]
    y = xy[1]
    text_width = draw.textlength(text, font=font)
    text_x = x - (text_width) / 2
    draw.text((text_x, y), text, fill=(0, 0, 0), font=font)
    return text_width


def draw_weather(image, draw, weather_list, weather_left, weather_top):
    weather_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)
    weather_font_temp_main = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 30)
    weather_font_temp_feels_like = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)
    weather_font_description = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 15)
    weather_width = 200

    if weather_list:
        for idx, weather in enumerate(weather_list):
            # load weather icon
            weather_icon = Image.open(weather.icon_path)

            # darken the image as light clouds etc are hard to see on the eink display
            enhancer = ImageEnhance.Brightness(weather_icon)
            weather_icon = enhancer.enhance(0.65)

            if idx == 0:
                weather_icon = weather_icon.resize((150, 150))
                weather_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)
                weather_font_temp_main = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 30
                )
                weather_font_temp_feels_like = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 20
                )
                weather_font_description = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 20
                )
                weather_width = 250
                weather_x_offset = 50
                temp_offset = 35
                feels_like_offset = 35
                description_offset = 60
                wind_offset = 25
            else:
                weather_icon = weather_icon.resize((85, 85))
                weather_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 17)
                weather_font_temp_main = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 25
                )
                weather_font_temp_feels_like = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 15
                )
                weather_font_description = ImageFont.truetype(
                    "fonts/FiraCode-Regular.ttf", 15
                )
                weather_x_offset = 10
                weather_width = 200
                temp_offset = 25
                feels_like_offset = 35
                description_offset = 30
                wind_offset = 15

            current_y = weather_top
            image.paste(weather_icon, box=(weather_left, current_y + 5))
            draw_centred(
                draw,
                (weather_left + (weather_width / 2), current_y),
                weather.time,
                font=weather_font,
            )

            current_y += temp_offset
            draw.text(
                (weather_left + weather_icon.width, current_y),
                f"{weather.temperature:.0f}°C",
                fill=(0, 0, 0),
                font=weather_font_temp_main,
            )

            current_y += feels_like_offset
            draw.text(
                (weather_left + weather_icon.width, current_y),
                f"({weather.feels_like:.0f}°C)",
                fill=(0, 0, 0),
                font=weather_font_temp_feels_like,
            )

            current_y += description_offset
            draw_centred(
                draw,
                (weather_left + weather_width / 2, current_y),
                weather.description,
                font=weather_font_description,
            )

            current_y += wind_offset
            draw_centred(
                draw,
                (weather_left + weather_width / 2, current_y),
                f"{weather.wind_speed_mph:.0f} mph ({weather.wind_gust_mph:.0f} mph gusts)",
                font=weather_font_description,
            )
            weather_left += weather_width + weather_x_offset


def draw_leaf_info(image: Image, image_draw: ImageDraw, leaf_info: LeafData):
    info_main_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 35)
    info_sub_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)

    cruising_range_ac_off_miles = leaf_info.cruising_range_ac_off_miles
    cruising_range_ac_on_miles = leaf_info.cruising_range_ac_on_miles

    image_draw.text(
        (110, 60),
        f"Range: {cruising_range_ac_off_miles:.0f} miles",
        fill=(0, 0, 0),
        font=info_main_font,
    )
    image_draw.text(
        (110, 100),
        f"({cruising_range_ac_on_miles:.0f} with climate control)",
        fill=(0, 0, 0),
        font=info_sub_font,
    )
    leaf_image = Image.open(leaf_info.icon_path)
    image.paste(leaf_image, box=(10, 40))


def draw_heading(image: Image, draw: ImageDraw, dashboard_data):
    heading_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 25)

    title = "Leeks Dashboard"
    title_width = draw.textlength(title, font=heading_font)
    title_x = (image.width / 2 - title_width) / 2
    draw.text((title_x, 10), title, fill=(0, 0, 0), font=heading_font)

    date_text = dashboard_data.date_string
    date_width = draw.textlength(date_text, font=heading_font)
    date_x = image.width - date_width - 10
    draw.text((date_x, 10), date_text, fill=(0, 0, 0), font=heading_font)
