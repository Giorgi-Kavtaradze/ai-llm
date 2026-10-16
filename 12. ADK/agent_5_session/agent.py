"""
Google ADK - 5. Sessions and State
A support agent that reads customer data from session state, replies with
structured output, and that output is written back into the state.

Run from this folder (it is a script, not an `adk web` agent):
    python agent.py

Needs GOOGLE_API_KEY in the .env file at the repo root.
"""

import asyncio
import time
import uuid
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from pydantic import BaseModel, Field


load_dotenv()

AGENT_MODEL = "gemini-flash-latest"


# output_schema forces the agent to reply with JSON matching this model,
# instead of free text. The Field descriptions tell the LLM what to fill in.
class CustomerStateOutput(BaseModel):
    customer_name: str = Field(description="Full name of the customer.")
    favorite_category: str = Field(
        description="Customer's preferred product category for shopping."
    )
    recent_order: str = Field(
        description="Details of the customer's most recent order including product, order number, and status."
    )
    loyalty_points: int = Field(
        description="Current number of loyalty/reward points the customer has earned.",
        ge=0,
    )


async def main():

    # The session service stores sessions. InMemory = lost when the script ends
    # (DatabaseSessionService has the same interface but saves to a database)
    session_service = InMemorySessionService()

    # Simple customer profile - this becomes the session's starting state
    customer_data = {
        "customer_name": "Sarah Johnson",
        "favorite_category": "Electronics",
        "recent_order": "iPhone 15 Pro - Order #12345 - Shipped",
        "loyalty_points": "500",
    }

    # Create the customer support agent
    support_agent = Agent(
        name="CustomerSupport",
        model=AGENT_MODEL,
        output_schema=CustomerStateOutput,
        # The agent's final (JSON) answer is saved into state under this key
        output_key="state",
        # {customer_name} etc. are filled in from session state on every call
        instruction="You are a friendly customer support agent for TechStore. Customer: {customer_name}. Their favorite category is {favorite_category}. Recent order: {recent_order}. Loyalty points: {loyalty_points}.",
    )

    # A session is identified by app name + user id + session id.
    # One user can have many sessions (conversations) in the same app.
    APP_NAME = "TechStore"
    CUSTOMER_ID = "sarah_j"
    SESSION_ID = str(uuid.uuid4())

    await session_service.create_session(
        app_name=APP_NAME,
        user_id=CUSTOMER_ID,
        session_id=SESSION_ID,
        state=customer_data,
    )

    print(f"🛒 Customer: {customer_data['customer_name']}")
    print(f"📱 Favorite: {customer_data['favorite_category']}")
    print(f"📦 Recent Order: {customer_data['recent_order']}")
    print(f"⭐ Points: {customer_data['loyalty_points']}")

    # The runner connects an agent to a session service: it loads the session,
    # runs the agent and saves the resulting events and state changes
    runner = Runner(
        agent=support_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # Messages to the agent are Content objects made of Parts (text, images...)
    customer_message = types.Content(
        role="user",
        parts=[types.Part(text="Hi! Can you check my recent order status?")],
    )

    print(f"customer_message: ==> {customer_message}")

    print(f"\n💬 Customer: Hi! Can you check my recent order status?")
    print("🤖 Support Agent: ", end="")

    # run_async yields events as they happen (tool calls, partial text...).
    # We only print the final response.
    async for event in runner.run_async(
        user_id=CUSTOMER_ID,
        session_id=SESSION_ID,
        new_message=customer_message,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                print(event.content.parts[0].text)

    # get_session returns a *copy* of the session, so changing session.state
    # directly would not be saved. State changes must go through an event.
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=CUSTOMER_ID, session_id=SESSION_ID
    )

    # Checks if structured output exists in session state under the output_key
    if "state" in session.state: # type: ignore
        structured_data = session.state["state"] # type: ignore
        print(structured_data)
        print("✅ Updating session state:")

        # Copy each field of the structured output into its own state key.
        # (The raw output stays under "state" - events can add or overwrite
        # keys, but not delete them.)
        state_delta = dict(structured_data)
        for key, value in structured_data.items():
            print(f"  - {key} updated to: {value}")

        # This is the official way to change state outside of an agent/tool:
        # append an event whose actions carry a state_delta
        await session_service.append_event(
            session, # type: ignore
            Event(
                author="system",
                invocation_id=str(uuid.uuid4()),
                actions=EventActions(state_delta=state_delta),
                timestamp=time.time(),
            ),
        )
    else:
        print("No structured output found in session state.")

    # Read the session again to show what was actually saved
    session = await session_service.get_session(
        app_name=APP_NAME, user_id=CUSTOMER_ID, session_id=SESSION_ID
    )
    print(f"\n📊 Session Data:")
    for key, value in session.state.items(): # type: ignore
        print(f"   {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
