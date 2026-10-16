"""
Google ADK - 5. Sessions: what a Session object contains
No LLM involved - just creates, inspects and deletes a session.

Run from this folder:
    python session_object.py
"""

from google.adk.sessions import InMemorySessionService
import asyncio
import uuid


async def main():
    # A session service creates, stores and loads sessions.
    # InMemorySessionService keeps them in memory only (lost when the script ends).
    temp_service = InMemorySessionService()
    example_session = await temp_service.create_session(
        app_name="my_app",
        user_id=f"user{uuid.uuid4()}",
        state={"initial_key": "Hello World for State!"},  # State can be initialized
    )

    print(f"--- Examining Session Properties ---")
    # Unique id of this conversation (generated if you don't pass session_id)
    print(f"ID (`id`):                {example_session.id}")
    # app_name + user_id + id together identify a session
    print(f"Application Name (`app_name`): {example_session.app_name}")
    print(f"User ID (`user_id`):         {example_session.user_id}")
    # state: a key-value scratchpad the agent and tools can read and write
    print(
        f"State (`state`):           {example_session.state}"
    )  # Note: Only shows initial state here
    # events: the conversation history (user messages, agent replies, tool calls)
    print(f"Events (`events`):         {example_session.events}")  # Initially empty
    print(f"Last Update (`last_update_time`): {example_session.last_update_time:.2f}")
    print(f"---------------------------------")

    # Clean up (optional for this example)
    await temp_service.delete_session(
        app_name=example_session.app_name,
        user_id=example_session.user_id,
        session_id=example_session.id,
    )

    # Loading a deleted session returns None
    deleted = await temp_service.get_session(
        app_name=example_session.app_name,
        user_id=example_session.user_id,
        session_id=example_session.id,
    )
    print("Session after delete - ", deleted)


if __name__ == "__main__":
    asyncio.run(main())
