from datetime import datetime, date
import json
import os

from . import config


def get_message(date_value: date | None):
    if os.path.isfile(config.messages_file):
        with open(config.messages_file) as f:
            messages = json.load(f)

        if not date_value:
            date_value = datetime.now().date()
        date_string = date_value.strftime("%Y-%m-%d")
        if date_string in messages:
            return messages[date_string]
        else:
            print("No message for ", date_string, flush=True)
            return ""
    else:
        print("No messages file: ", config.messages_file, flush=True)
        return ""


def set_message(date_value: date, message: str):
    if os.path.isfile(config.messages_file):
        with open(config.messages_file) as f:
            messages = json.load(f)
    else:
        messages = {}

    date_string = date_value.strftime("%Y-%m-%d")
    messages[date_string] = message

    with open(config.messages_file, "w") as f:
        json.dump(messages, f, indent=4)
        print("Wrote message for ", date_string, flush=True)
