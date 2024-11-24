from dataclasses import dataclass
from datetime import datetime
import json
import os

from . import config


@dataclass
class TemperatureData:
    reported_at: datetime
    temperature: float
    humidity: float


def get_all_temperature_data() -> dict[str, TemperatureData]:
    """
    Get the temperature data
    Returns a dict keyed on the temperature name
    """
    temperature_data_file = os.path.join(
        config.dashboard_input_dir, "temperatures.json")

    if not os.path.isfile(temperature_data_file):
        print("ERROR: temperatures.json does not exist")
        return None

    result = {}
    with open(temperature_data_file) as f:
        temperature_data = json.load(f)
        print(temperature_data)
        for temp in temperature_data["temperatures"]:
            temp_data = temperature_data["temperatures"][temp]
            temperature = TemperatureData(
                reported_at=temp_data["reported_at"],
                temperature=temp_data["temperature"], humidity=temp_data["humidity"])
            result[temp] = temperature
    return result


def update_temperature_data(name: str, temperature: float, humidity: float):
    temperature_data_file = os.path.join(
        config.dashboard_input_dir, "temperatures.json")

    if os.path.isfile(temperature_data_file):
        with open(temperature_data_file) as f:
            temperatures = json.load(f)
    else:
        temperatures = {"temperatures": {}}

    temperature_data = temperatures["temperatures"]
    temperature_data[name] = {
        "reported_at": datetime.now().isoformat(),
        "temperature": temperature,
        "humidity": humidity,
    }
    with open(temperature_data_file, "w") as f:
        json.dump(temperatures, f, indent=4)
