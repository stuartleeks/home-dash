#!/usr/bin/env python

import json
import os
import time
import logging
import sys

from PIL import Image, ImageDraw, ImageFont

from dotenv import load_dotenv

load_dotenv()

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='LEAF:%(asctime)s:%(levelname)s: %(message)s')

dashboard_input_dir = os.getenv("DASHBOARD_INPUT_DIR")

if not dashboard_input_dir:
    print("ERROR: DASHBOARD_INPUT_DIR not set")
    sys.exit(1)
    
if not os.path.isdir(dashboard_input_dir):
    print("ERROR: DASHBOARD_INPUT_DIR does not exist")
    sys.exit(1)

# Get the leaf summary content from leaf-summary.json
leaf_summary_file = os.path.join(dashboard_input_dir, "leaf-summary.json")

if not os.path.isfile(leaf_summary_file):
    print("ERROR: leaf-summary.json does not exist")
    sys.exit(1)

with open(leaf_summary_file) as f:
    leaf_summary = json.load(f)


# print(leaf_summary)


image = Image.new(mode='RGB',size= (800, 480), color = (255, 255, 255))

draw = ImageDraw.Draw(image)

font = ImageFont.load_default(20)

draw.text((10, 10), "Home Dashboard", fill=(0,0,0), font=font)

leaf_range = leaf_summary["estimated_range"]
draw.text((10, 30), f"Car range: {leaf_range:.0f} miles", fill=(0,0,0))

image.save("test.jpg")