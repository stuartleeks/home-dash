from dotenv import load_dotenv
import os


if "SKIP_DOTENV" not in os.environ:
    load_dotenv()


app_insights_connection_string = os.getenv(
    "APPLICATIONINSIGHTS_CONNECTION_STRING")

script_dir = os.path.dirname(os.path.abspath(__file__))
leaf_image_dir = os.path.join(script_dir, "leaf_images")


dashboard_input_dir = os.getenv("DASHBOARD_INPUT_DIR")

messages_file = os.getenv("MESSAGES_FILE") or os.path.join(
    dashboard_input_dir, "messages.json"
)
print(f"Using messages file: {messages_file}")

