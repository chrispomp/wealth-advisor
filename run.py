# /wealth-advisor/run.py

import asyncio
from google.adk.runners import InMemoryRunner
from main import create_agent

async def main():
    """Runs the AI Wealth Advisor agent."""
    agent = create_agent()
    runner = InMemoryRunner(agent=agent)
    user_id = "local-user"
    session_id = "local-session"

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        async for event in runner.run_async(
            user_id=user_id, session_id=session_id, new_message=user_input
        ):
            if event.is_final_response():
                print(f"AI Wealth Advisor: {event.text}")

if __name__ == "__main__":
    asyncio.run(main())