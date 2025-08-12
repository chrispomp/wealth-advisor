# /wealth-advisor/main.py

import os
import json
import logging
import asyncio

from flask import Flask, request
from google.cloud import secretmanager
import vertexai
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
from google.genai.types import Content, Part

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
    """Sets the Alpha Vantage API key."""
    # Replace the placeholder with your actual API key
    os.environ["ALPHA_VANTAGE_API_KEY"] = "NZJEA6QEWNX6IFRC"
    logging.info("Successfully set Alpha Vantage API key.")

# --- Agent Definition ---
def create_agent():
    """Creates the AI Wealth Advisor agent."""
    vertexai.init(project=GCP_PROJECT_ID, location="us-central1")
    
    return LlmAgent(
        name="ai_wealth_advisor",
        model="gemini-2.5-flash",
        instruction=AGENT_INSTRUCTIONS,
        tools=[
            get_user_portfolio_summary,
            get_market_news_and_sentiment,
            get_citi_perspective,
        ],
    )

agent = create_agent()
runner = InMemoryRunner(agent=agent)

@app.route("/chat", methods=["POST"])
async def chat_handler():
    """
    Handles the chat requests for a single client session.
    """
    if not request.is_json:
        return "Request should be in JSON format", 400

    request_data = request.get_json()
    if "message" not in request_data:
        return "Missing 'message' in request", 400

    message = request_data["message"]
    user_id = "user-123"  # Replace with actual user management
    session_id = "session-456" # Replace with actual session management
    
    response_parts = []
    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=Content(parts=[Part.from_text(text=message)])
    ):
        if event.is_final_response() and event.content:
            response_parts.append(event.content.parts[0].text)

    return json.dumps({"response": "".join(response_parts)})

# --- Main Entry Point ---
if __name__ == "__main__":
    get_alpha_vantage_api_key()
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))