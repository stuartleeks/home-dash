from dataclasses import dataclass
import json
import os

from . import config

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

def get_leaf_summary():
    # Get the leaf summary content from leaf-summary.json
    leaf_summary_file = os.path.join(config.dashboard_input_dir, "leaf-summary.json")

    if not os.path.isfile(leaf_summary_file):
        print("ERROR: leaf-summary.json does not exist")
        return {"error": "leaf-summary.json does not exist"}

    with open(leaf_summary_file) as f:
        leaf_summary = json.load(f)

    return leaf_summary

def get_leaf_icon(plugged_in: bool, charging: bool):
    if plugged_in:
        if charging:
            return LEAF_ICON_CHARGING
        return LEAF_ICON_PLUGGED_IN
    return LEAF_ICON_NOT_PLUGGED_IN


def get_leaf_data():
    leaf_summary = get_leaf_summary()

    plugged_in = leaf_summary["is_connected"]
    charging = leaf_summary["charging_status"] != "NOT_CHARGING"
    leaf_icon = get_leaf_icon(plugged_in, charging)
    leaf_data = LeafData(
        cruising_range_ac_off_miles=leaf_summary["cruising_range_ac_off_miles"],
        cruising_range_ac_on_miles=leaf_summary["cruising_range_ac_on_miles"],
        is_plugged_in=plugged_in,
        is_charging=charging,
        icon_path=os.path.join(config.leaf_image_dir, leaf_icon),
    )

    return leaf_data
