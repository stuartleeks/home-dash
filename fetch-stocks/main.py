from dataclasses import asdict, dataclass
from datetime import datetime
import json
import os
import requests
import sys

from dotenv import load_dotenv

if "SKIP_DOTENV" not in os.environ:
    load_dotenv()


output_dir = os.getenv("OUTPUT_DIR")
if not output_dir:
    print("ERROR: OUTPUT_DIR not set")
    sys.exit(1)
if not os.path.isdir(output_dir):
    os.makedirs(output_dir)
output_file = os.path.join(output_dir, "stocks.json")

stocks_api_key = os.getenv("STOCKS_API_KEY")
if not stocks_api_key:
    print("ERROR: STOCKS_API_KEY not set")
    exit(1)
      

stocks = [s.strip() for s in os.getenv("STOCKS").split(",")]

# stock_url_param=
url = f"https://api.stockdata.org/v1/data/quote?symbols={','.join(stocks)}&api_token={stocks_api_key}"

response = requests.get(url)
if response.status_code != 200:
    print(f"ERROR: API request failed with status code {response.status_code}")
    print(response.text)
    exit(1)

response_json = response.json()

stock_results = []
for stock in response_json["data"]:
    stock_results.append({
        "symbol": stock["ticker"],
        "price": stock["price"],
        "currency": stock["currency"],
    })

result = {
    "stocks": stock_results
}

print(result)
json.dump(result, open(output_file, "w"))

