from dataclasses import dataclass

import os
import json

from . import config

@dataclass
class StockData:
    symbol: str
    price: float
    currency: str


def get_stock_data():
    # Get the stock data from stocks.json
    stocks_file = os.path.join(config.dashboard_input_dir, "stocks.json")

    if not os.path.isfile(stocks_file):
        print("ERROR: stocks.json does not exist")
        sys.exit(1)  # TODO - handle this gracefully!

    with open(stocks_file) as f:
        stocks_data = json.load(f)

    stocks = [
        StockData(symbol=s["symbol"], price=s["price"], currency=s["currency"])
        for s in stocks_data["stocks"]
    ]
    return stocks
