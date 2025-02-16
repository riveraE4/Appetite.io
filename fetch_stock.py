import sqlite3
from fuzzywuzzy import process

def find_stock(user_input):
#connect to the database
    conn = sqlite3.connect("tickers.db")
    cursor = conn.cursor()

    #test query
    cursor.execute("SELECT symbol, company_name, nickname FROM tickers;")
    tickers = cursor.fetchall()

    #close connection
    conn.close()

    all_names = {symbol: company for symbol, company, nickname in tickers}

    for symbol, company, nickname in tickers:
        if user_input.lower() in [symbol.lower(), nickname.lower()]:
            return symbol

    best_match, score = process.extractOne(user_input, all_names.values())
    if score > 80:
        return all_names[best_match]
    elif score > 60:
        print(f"Did you mean {best_match}?")
        confirm = input("Type 'Y' to confirm, or 'N' to cancel: ")
        if confirm == 'y' | 'Y':
            return all_names[best_match]
        else:
            return "Stock not found! Please try again!"
    else:
        return "Stock not found in database"


def clean_user_input(user_input):
    """takes user stock input, removes extra spaces and standardizes it"""
    clean_input = user_input.strip()
    clean_input = clean_input.lower()
    return clean_input


user_stock = input("Enter stock ticker or company name: ")
result = find_stock(user_stock)
print("Stock Ticker:", result)

