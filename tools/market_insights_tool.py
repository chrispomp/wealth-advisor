# /wealth-advisor/tools/market_insights_tool.py

import requests
import os
import json
import logging
from typing import Optional

API_ENDPOINT = "https://www.alphavantage.co/query"

def get_market_news_and_sentiment(tickers: Optional[str] = None, topics: Optional[str] = None) -> str:
    """
    Retrieves up to 5 latest news articles and their sentiment for given stock tickers or topics from Alpha Vantage.
    You can specify tickers (e.g., 'AAPL,IBM'), topics (e.g., 'technology,ipo'), or both.
    Returns a JSON string with news title, summary, URL, and sentiment.
    """
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY")
    if not api_key or api_key == "key_not_found":
        return json.dumps({"error": "Alpha Vantage API key is not configured."})
        
    if not tickers and not topics:
        return json.dumps({"error": "Please provide at least one ticker or topic."})

    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": api_key,
        "limit": 5,
    }
    if tickers:
        params['tickers'] = tickers.upper()
    if topics:
        params['topics'] = topics.lower()

    try:
        logging.info(f"Fetching market news with params: {params}")
        response = requests.get(API_ENDPOINT, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        if "feed" in data and data["feed"]:
            articles = [
                {
                    "title": item.get("title"),
                    "summary": item.get("summary"),
                    "url": item.get("url"),
                    "sentiment": item.get("overall_sentiment_label")
                }
                for item in data["feed"]
            ]
            return json.dumps(articles)
        else:
            logging.warning(f"No news found or API error from Alpha Vantage. Response: {data}")
            return json.dumps({"error": "No news found or an API error occurred.", "details": data.get("Information", data)})
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to retrieve news from Alpha Vantage: {e}")
        return json.dumps({"error": f"Failed to retrieve news from Alpha Vantage: {e}"})