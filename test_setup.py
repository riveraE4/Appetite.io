import requests
import pandas as pd
import numpy as np
from fastapi import FastAPI

# Check if libraries are working
print("✅ Requests version:", requests.__version__)
print("✅ Pandas version:", pd.__version__)
print("✅ NumPy version:", np.__version__)

# Test API Call (Using Alpha Vantage)
API_KEY = "demo"  # Replace with a real API key later
STOCK_SYMBOL = "AAPL"

url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={STOCK_SYMBOL}&apikey={API_KEY}"
response = requests.get(url)

if response.status_code == 200:
    print("✅ Successfully fetched stock data!")
else:
    print("❌ API request failed.")

# Test FastAPI instance
app = FastAPI()

@app.get("/")
def home():
    return {"message": "FastAPI is working!"}

