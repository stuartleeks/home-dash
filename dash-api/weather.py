from dataclasses import dataclass
import json
import os

from . import config

@dataclass
class WeatherDataPoint:
    time: str
    description: str
    temperature: float
    feels_like: float
    icon_path: str
    wind_speed_mph: float
    wind_gust_mph: float | None

@dataclass
class WeatherData:
    current: WeatherDataPoint
    forecast: list[WeatherDataPoint]

def get_weather_data():
    # Get the leaf summary content from leaf-summary.json
    weather_summary_file = os.path.join(
        config.dashboard_input_dir, "weather-summary.json")

    if not os.path.isfile(weather_summary_file):
        print("ERROR: weather-summary.json does not exist")
        return None

    with open(weather_summary_file) as f:
        weather_summary_json = json.load(f)
        # parse the json into a list of WeatherData objects
        weather_data = []
        for weather in weather_summary_json["forecast"]:
            weather_data.append(WeatherDataPoint(**weather))

        current = WeatherDataPoint(**weather_summary_json["current"])

    return WeatherData(current=current, forecast=weather_data)



def get_rounded_weather_data(weather_data: WeatherDataPoint) -> WeatherDataPoint:
    return WeatherDataPoint(
        time=weather_data.time,
        description=weather_data.description,
        temperature=round(weather_data.temperature),
        feels_like=round(weather_data.feels_like),
        icon_path=weather_data.icon_path,
        wind_speed_mph=round(weather_data.wind_speed_mph),
        wind_gust_mph=(
            round(weather_data.wind_gust_mph) if weather_data.wind_gust_mph else None
        ),
    )