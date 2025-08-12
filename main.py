# /wealth-advisor/main.py

import os
import json
import asyncio
import logging

from flask import Flask, request
from google.cloud import secretmanager
from google import genai

# --- Local Tool Imports ---
from tools.portfolio_tool import get_user_portfolio_summary
from tools.market_insights_tool import get_market_news_and_sentiment
from tools.citi_perspective_tool import get_citi_perspective

# --- Configuration & Initialization ---
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID")
AGENT_INSTRUCTIONS = """
You are a friendly and professional AI Wealth Advisor for Citi.
- Your responses must be concise, clear, and easy to understand.
- Before answering questions about market outlook, recommendations, policies, or procedures, YOU MUST use the `get_citi_perspective` tool to retrieve the official Citi viewpoint.
- Use the `get_user_portfolio_summary` tool for any questions about the user's own portfolio performance or composition. If you do not know the user's client_id, you must ask for it first.
- Use the `get_market_news_and_sentiment` tool for general questions about external company news or stock market sentiment.
- Never provide financial advice; always include the mandatory disclaimer if it's the first turn of the conversation. This is a mandatory requirement.
- Do not answer questions outside the scope of finance and portfolio management.
"""

# --- Secret & API Key Management ---
def get_alpha_vantage_api_key():
    """Fetches the Alpha Vantage API key from Google Secret Manager."""
    try:
        secret_id = os.environ.get("ALPHA_VANTAGE_API_KEY_SECRET")
        if not secret_id:
            raise ValueError("ALPHA_VANTAGE_API_KEY_SECRET environment variable not set.")
            
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        api_key = response.payload.data.decode("UTF-8")
        os.environ["ALPHA_VANTAGE_API_KEY"] = api_key
        logging.info("Successfully fetched Alpha Vantage API key.")
    except Exception as e:
        logging.error(f"Failed to fetch Alpha Vantage API key: {e}")
        # In a real app, you might want to handle this more gracefully
        # For this example, we'll proceed and let the tool fail if the key is missing.
        os.environ["ALPHA_VANTAGE_API_KEY"] = "key_not_found"

# --- Agent Definition ---
# Initialize the generative AI client
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
model = genai.GenerativeModel(
    model_name="gemini-1.5-pro-latest",
    system_instruction=AGENT_INSTRUCTIONS,
    tools=[
        get_user_portfolio_summary,
        get_market_news_and_sentiment,
        get_citi_perspective,
    ],
)

@app.route("/chat", methods=["POST"])
def chat_handler():
    """
    Handles the chat requests for a single client session.
    - Note: JWT authentication would be added here in a production system.
    """
    if not request.is_json:
        return "Request should be in JSON format", 400

    request_data = request.get_json()
    if "message" not in request_data:
        return "Missing 'message' in request", 400

    message = request_data["message"]
    chat = model.start_chat()
    response = chat.send_message(message)

    return json.dumps({"response": response.text})


# --- Main Entry Point ---
if __name__ == "__main__":
    get_alpha_vantage_api_key()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))