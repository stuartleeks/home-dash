from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
import requests
import sys

from dotenv import load_dotenv

if "SKIP_DOTENV" not in os.environ:
    load_dotenv()

miles_per_km = 0.62137119

openweather_api_key = os.getenv("OPENWEATHER_API_KEY")
if not openweather_api_key:
    print("ERROR: OPENWEATHER_API_KEY not set")
    exit(1)

lat = os.getenv("OPENWEATHER_LAT")
lng = os.getenv("OPENWEATHER_LNG")
if not lat or not lng:
    print("ERROR: OPENWEATHER_LAT or OPENWEATHER_LNG not set")
    exit(1)

output_dir = os.getenv("OUTPUT_DIR")
if not output_dir:
    print("ERROR: OUTPUT_DIR not set")
    sys.exit(1)
if not os.path.isdir(output_dir):
    os.makedirs(output_dir)
output_file = os.path.join(output_dir, "weather-summary.json")


def download_icon(icon_name: str) -> str:
    icon_url = f"https://openweathermap.org/img/wn/{icon_name}@2x.png"
    icon_folder = os.path.join(output_dir, "weather-icons")
    if not os.path.isdir(icon_folder):
        os.makedirs(icon_folder)
    icon_path = os.path.join(icon_folder, f"{icon_name}.png")
    if not os.path.isfile(icon_path):
        icon_response = requests.get(icon_url)
        with open(icon_path, "wb") as f:
            f.write(icon_response.content)
    return icon_path


@dataclass
class WeatherData:
    time: str
    description: str
    temperature: float
    feels_like: float
    icon_path: str
    wind_speed_mph: float
    wind_gust_mph: float | None


def get_current_weather() -> WeatherData:
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lng}&appid={openweather_api_key}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        print(f"ERROR: OpenWeather API returned {response.status_code}")
        exit(1)

    time = "Now"
    weather = response.json()
    description = weather["weather"][0]["description"]
    icon_name = weather["weather"][0]["icon"]
    temp = weather["main"]["temp"]
    feels_like = weather["main"]["feels_like"]

    icon_path = download_icon(icon_name)

    wind_speed = weather["wind"]["speed"]
    wind_gust = weather["wind"].get("gust")

    wind_speed_mph = wind_speed * miles_per_km
    wind_gust_mph = wind_gust * miles_per_km if wind_gust else None

    return WeatherData(
        time=time,
        description=description,
        temperature=temp,
        feels_like=feels_like,
        icon_path=icon_path,
        wind_speed_mph=wind_speed_mph,
        wind_gust_mph=wind_gust_mph,
    )


def parse_forecast_data(forecast: dict) -> WeatherData:
    dt = forecast["dt"]
    dt_object = datetime.fromtimestamp(dt)
    time = dt_object.strftime("%H:%M")

    description = forecast["weather"][0]["description"]
    icon_name = forecast["weather"][0]["icon"]
    temp = forecast["main"]["temp"]
    feels_like = forecast["main"]["feels_like"]

    wind_speed = forecast["wind"]["speed"]
    wind_gust = forecast["wind"].get("gust")

    wind_speed_mph = wind_speed * miles_per_km
    wind_gust_mph = wind_gust * miles_per_km if wind_gust else None

    icon_path = download_icon(icon_name)

    return WeatherData(
        time=time,
        description=description,
        temperature=temp,
        feels_like=feels_like,
        icon_path=icon_path,
        wind_speed_mph=wind_speed_mph,
        wind_gust_mph=wind_gust_mph,
    )


def get_weather_forecast() -> list[WeatherData]:
    url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lng}&appid={openweather_api_key}&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        print(
            f"ERROR: OpenWeather API (forecast) returned {response.status_code}")
        exit(1)

    list = response.json()["list"]
    return [parse_forecast_data(forecast) for forecast in list]


weather_data = get_weather_forecast()

summary = {
    "current": asdict(get_current_weather()),
    "forecast": [asdict(w) for w in weather_data],
}
# print(summary)

json.dump(summary, open(output_file, "w"), indent=2)
