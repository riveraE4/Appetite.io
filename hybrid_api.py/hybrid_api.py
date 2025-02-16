from flask import Flask, jsonify, request
import sqlite3
import requests
import redis
import json
import time

# Initialize Flask app
app = Flask(__name__)

# API Keys
ALPHA_VANTAGE_API_KEY = "your_alpha_vantage_api_key"
FINNHUB_API_KEY = "your_finnhub_api_key"
IEX_CLOUD_API_KEY = "your_iex_cloud_api_key"

# Redis Cache Setup
redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

# SQLite Database Setup
def get_db_connection():
    return sqlite3.connect("tickers.db")

def setup_db():
    """Creates tables for storing stock data."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stocks (
            ticker TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            sector TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_prices (
            ticker TEXT PRIMARY KEY,
            open_price REAL,
            close_price REAL,
            high REAL,
            low REAL,
            volume INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        conn.commit()

# Rate limiting function to avoid API bans
def throttle_request():
    time.sleep(1.5)  # Add a slight delay between API requests

# -------------------------------
# 1️⃣ Search for Stock Ticker
# -------------------------------
def get_valid_ticker(query):
    """Tries Finnhub, IEX Cloud, and Alpha Vantage to find a stock ticker."""
    throttle_request()
    
    # 1️⃣ Try Finnhub
    url_finnhub = f"https://finnhub.io/api/v1/search?q={query}&token={FINNHUB_API_KEY}"
    response = requests.get(url_finnhub)
    if response.status_code == 200:
        data = response.json()
        if "result" in data and len(data["result"]) > 0:
            return data["result"][0]["symbol"]

    # 2️⃣ Try IEX Cloud
    url_iex = f"https://cloud.iexapis.com/stable/search/{query}?token={IEX_CLOUD_API_KEY}"
    response = requests.get(url_iex)
    if response.status_code == 200:
        data = response.json()
        if len(data) > 0:
            return data[0]["symbol"]

    # 3️⃣ Try Alpha Vantage
    url_alpha = f"https://www.alphavantage.co/query?function=SYMBOL_SEARCH&keywords={query}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url_alpha)
    if response.status_code == 200:
        data = response.json()
        if "bestMatches" in data and len(data["bestMatches"]) > 0:
            return data["bestMatches"][0]["1. symbol"]

    return None  # No valid ticker found

# -------------------------------
# 2️⃣ Get Stock Price
# -------------------------------
def get_stock_price(ticker):
    """Fetches stock price from Finnhub, IEX Cloud, or Alpha Vantage."""
    
    # 1️⃣ Check Redis cache first
    cached_data = redis_client.get(f"{ticker}_price")
    if cached_data:
        return json.loads(cached_data)

    # 2️⃣ Try Finnhub for real-time prices
    url_finnhub = f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}"
    response = requests.get(url_finnhub)
    if response.status_code == 200:
        data = response.json()
        if "c" in data:
            redis_client.setex(f"{ticker}_price", 3600, json.dumps(data))
            return data

    # 3️⃣ Try IEX Cloud
    url_iex = f"https://cloud.iexapis.com/stable/stock/{ticker}/quote?token={IEX_CLOUD_API_KEY}"
    response = requests.get(url_iex)
    if response.status_code == 200:
        data = response.json()
        if "latestPrice" in data:
            redis_client.setex(f"{ticker}_price", 3600, json.dumps(data))
            return data

    # 4️⃣ Try Alpha Vantage
    url_alpha = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={ticker}&interval=5min&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url_alpha)
    if response.status_code == 200:
        data = response.json()
        if "Time Series (5min)" in data:
            latest_time = list(data["Time Series (5min)"].keys())[0]
            latest_data = data["Time Series (5min)"][latest_time]
            redis_client.setex(f"{ticker}_price", 3600, json.dumps(latest_data))
            return latest_data

    return None  # No valid data found

# -------------------------------
# 3️⃣ Flask API Endpoints
# -------------------------------
@app.route("/ticker/<company_name>", methods=["GET"])
def search_ticker(company_name):
    """Finds the stock ticker for a given company name."""
    ticker = get_valid_ticker(company_name)
    if ticker:
        return jsonify({"ticker": ticker}), 200
    return jsonify({"error": "Ticker not found"}), 404

@app.route("/price/<ticker>", methods=["GET"])
def stock_price(ticker):
    """Returns the latest stock price for a given ticker."""
    price_data = get_stock_price(ticker)
    if price_data:
        return jsonify(price_data), 200
    return jsonify({"error": "Stock price not found"}), 404

@app.route("/history/<ticker>", methods=["GET"])
def stock_history(ticker):
    """Fetches the last 7 days of stock history."""
    url_alpha = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={ticker}&apikey={ALPHA_VANTAGE_API_KEY}"
    response = requests.get(url_alpha)
    if response.status_code == 200:
        data = response.json()
        return jsonify(data["Time Series (Daily)"]), 200

    return jsonify({"error": "Stock history not available"}), 404

# -------------------------------
# Run Flask App
# -------------------------------
if __name__ == "__main__":
    setup_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
