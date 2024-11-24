from datetime import datetime
import json
import os

from . import config

def get_message():
    if os.path.isfile(config.messages_file):
        with open(config.messages_file) as f:
            messages = json.load(f)

        date_string = datetime.now().strftime("%Y-%m-%d")
        if date_string in messages:
            return messages[date_string]
        else:
            print("No message for ", date_string, flush=True)
            return ""
    else:
        print("No messages file: ", config.messages_file, flush=True)
        return ""

