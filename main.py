from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from io import BytesIO
import json
import logging
import os
import requests
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
class WeatherData:
    description: str
    temperature: float
    icon_path: str

def get_weather():
    # TODO: cache responses
    openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
    if not openweather_api_key:
        print("ERROR: OPENWEATHER_API_KEY not set")
        return None
    
    lat = os.getenv("OPENWEATHER_LAT")
    lng = os.getenv("OPENWEATHER_LNG")
    if not lat or not lng:
        print("ERROR: OPENWEATHER_LAT or OPENWEATHER_LNG not set")
        return None

    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={openweather_api_key}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"ERROR: OpenWeather API returned {response.status_code}")
        return None
    
    weather = response.json()
    description = weather["weather"][0]["description"]
    icon_name = weather["weather"][0]["icon"]
    temp = weather["main"]["temp"]
    
    icon_url = f"https://openweathermap.org/img/wn/{icon_name}@2x.png"
    icon_folder = os.path.join(dashboard_input_dir, "weather-icons")
    if not os.path.isdir(icon_folder):
        os.makedirs(icon_folder)
    icon_path = os.path.join(icon_folder, f"{icon_name}.png")
    if not os.path.isfile(icon_path):
        icon_response = requests.get(icon_url)
        with open(icon_path, "wb") as f:
            f.write(icon_response.content)

    return WeatherData(description=description, temperature=temp, icon_path=icon_path)



def get_message():
    print (dashboard_input_dir)
    messages_file = os.path.join(dashboard_input_dir, "messages.json")

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
    estimated_range: float
    is_plugged_in: bool
    is_charging: bool


@dataclass
class DashboardData:
    leaf: LeafData
    date_string: str
    message: str
    weather: WeatherData


def get_dashboard_data():
    leaf_summary = get_leaf_summary()

    dashboard_data = DashboardData(
        leaf=LeafData(
            estimated_range=leaf_summary["estimated_range"],
            is_plugged_in=leaf_summary["is_connected"],
            is_charging=leaf_summary["charging_status"] != "NOT_CHARGING",
        ),
        date_string=datetime.now().strftime("%A, %d %B %Y"),
        message=get_message(),
        weather=get_weather(),
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
    background = Image.new('RGB', image.size, color)
    background.paste(image, mask=image.split()[3])  # 3 is the alpha channel
    return background


@app.get("/dashboard-image")
def get_dashboard_image(request: Request):
    dashboard_data = get_dashboard_data()

    data_hash = hash_data(dashboard_data)
    if "If-None-Match" in request.headers:
        if_none_match_value = request.headers["If-None-Match"]
        print(f"**Got IfNoneMatch: '{if_none_match_value}'", flush=True)
        if request.headers["If-None-Match"] == str(data_hash):
            return Response(status_code=304)

    image = Image.new(mode="RGBA", size=(800, 480), color=(255, 255, 255))

    draw = ImageDraw.Draw(image)

    message_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 25)
    info_main_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 35)
    heading_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 25)
    info_sub_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 25)
    weather_font = ImageFont.truetype("fonts/FiraCode-Regular.ttf", 20)

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

    # load weather icon
    weather_icon = Image.open(dashboard_data.weather.icon_path)
    image.paste(weather_icon, box= (10, 120))
    draw.text(
        (10 + weather_icon.width + 10, 130),
        f"Current: {dashboard_data.weather.temperature:.0f}°C {dashboard_data.weather.description}",
        fill=(0, 0, 0),
        font=weather_font,
    )

    message = dashboard_data.message
    message_width = draw.textlength(message, font=heading_font)
    message_x = (image.width - message_width) / 2
    draw.text((message_x, 400), message, fill=(0, 0, 0), font=message_font)

    # handle the alpha channel (needed for PNGs from OpenWeatherMap)
    image = pure_pil_alpha_to_color_v2(image)

    image_buf = BytesIO()
    image.save(image_buf, "JPEG")
    image_buf.seek(0)

    return StreamingResponse(
        image_buf, media_type="image/jpeg", headers={"ETag": str(data_hash)}
    )
