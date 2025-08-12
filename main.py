# /wealth-advisor/main.py

import os
import json
import asyncio
import logging

from flask import Flask
from websockets.server import serve
from google.cloud import secretmanager
import google.generativeai as genai
from google.generativeai.experimental import adk

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
agent = adk.GenerativeAgent(
    model="models/gemini-1.5-pro-latest",
    tools=[
        get_user_portfolio_summary,
        get_market_news_and_sentiment,
        get_citi_perspective,
    ],
    system_instruction=AGENT_INSTRUCTIONS,
    # Enable live audio streaming
    enable_live_audio=True,
    live_audio_config=adk.LiveAudioConfig(
        sample_rate_hertz=16000,
        encoding="LINEAR16" # LINEAR16
    ),
)

# --- WebSocket Server Logic ---
async def chat_handler(websocket, path):
    """
    Handles the WebSocket connection for a single client session.
    - Note: JWT authentication would be added here in a production system.
    """
    logging.info(f"Client connected from {websocket.remote_address}")
    try:
        # Create an audio stream processor for the agent
        async for audio_chunk in websocket:
            # Stream client audio to the agent
            await agent.stream_audio_content(audio_chunk)

        # Receive the agent's final response and stream it back
        async for chunk in agent.stream_response_content():
            if chunk.text:
                logging.info(f"Sending text chunk to client: {chunk.text}")
            if chunk.audio:
                logging.info(f"Sending audio chunk of size {len(chunk.audio)} to client.")
                await websocket.send(chunk.audio)

    except Exception as e:
        logging.error(f"Connection error: {e}")
    finally:
        logging.info(f"Client disconnected from {websocket.remote_address}")
        # Clean up agent state for the next session
        agent.new_chat()

async def start_websocket_server():
    """Starts the WebSocket server."""
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", 8080))
    logging.info(f"Starting WebSocket server on {host}:{port}")
    async with serve(chat_handler, host, port):
        await asyncio.Future() # Run forever

# --- Main Entry Point ---
if __name__ == "__main__":
    get_alpha_vantage_api_key()
    try:
        asyncio.run(start_websocket_server())
    except KeyboardInterrupt:
        logging.info("Server shutting down.")

# Note: For Gunicorn deployment, you'd have a separate config.
# This structure is primarily for direct execution and conceptual clarity.
# Gunicorn will run the Flask app, and a separate process or thread
# would manage the asyncio event loop for the websocket server.
# A more integrated approach uses libraries like Flask-Sockets or Quart.