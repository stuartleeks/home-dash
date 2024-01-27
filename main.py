import json
import logging
import os
import sys
from fastapi import FastAPI

app = FastAPI()


from dotenv import load_dotenv

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
