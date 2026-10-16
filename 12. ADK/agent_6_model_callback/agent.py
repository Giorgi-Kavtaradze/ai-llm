"""
Google ADK - 6. Model Callbacks
Intercept and modify what goes TO and FROM the LLM.

    before_model_callback: runs before every LLM call (filter, log, block)
    after_model_callback:  runs after every LLM reply (edit, add disclaimers)

Run from the "12. ADK" folder:
    adk web                          (then pick agent_6_model_callback in the dropdown)
    adk run agent_6_model_callback   (chat in the terminal)

Try: "Hi, how are you?" (goes to the model) and "This damn app is crap" (blocked).
Needs GOOGLE_API_KEY in the .env file at the repo root.
"""

import re
from typing import Optional
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

load_dotenv()

AGENT_MODEL = "gemini-flash-latest"

# Example profanity filter (a small word list - real apps use bigger lists or
# a moderation model). \b = whole words only, which avoids blocking innocent
# words that contain a bad one: "class", "Scunthorpe", "Dickens"...
# The endings cover common variants: "fucking", "bullshit", "damn it".
PROFANITY_PATTERN = re.compile(
    r"\b(fuck\w*|\w*shit\w*|bitch(es|y)?|bastards?|assholes?|damn(ed|it)?|crap(py)?)\b",
    re.IGNORECASE,
)


def before_model_callback(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """
    Called BEFORE sending the request to the AI model.
    Perfect for: content filtering, request logging, blocking inappropriate content

    Return None to continue, or an LlmResponse to skip the model and use that
    response instead.
    """
    # llm_request.contents is the whole conversation, so search from the end
    # to get the LATEST user message (not the first one)
    user_message = ""
    for content in reversed(llm_request.contents or []):
        if content.role == "user" and content.parts:
            # A part can have no text (e.g. an image), so fall back to ""
            user_message = content.parts[0].text or ""
            break

    print(f"📤 Sending to model: '{user_message}'")

    # Block messages with profanity
    if PROFANITY_PATTERN.search(user_message):
        print("🚫 Blocking message with profanity!")

        # Callbacks can read and write session state too - here we count how
        # many messages were blocked (visible in the State tab of `adk web`)
        blocked = callback_context.state.get("blocked_messages", 0)
        callback_context.state["blocked_messages"] = blocked + 1

        # Return a custom response instead of calling the model.
        # The model is never called, so this costs no tokens - and
        # after_model_callback does not run for it either.
        return LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(
                        text="Let's keep it friendly! Please rephrase your "
                        "message without the bad language."
                    )
                ],
            )
        )

    print("✅ Request approved - sending to model")
    return None  # Continue to model


def after_model_callback(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """
    Called AFTER getting response from the AI model.
    Perfect for: response filtering, adding disclaimers, logging responses

    Return None to keep the response, or an LlmResponse to replace it.
    """
    # Find the last text part of the response (some parts have no text)
    parts = llm_response.content.parts if llm_response.content else None
    for part in reversed(parts or []):
        if part.text:
            print(f"📥 Model responded: '{part.text[:50]}...'")

            # Add a fun emoji to every response.
            # We edit the response in place, which keeps everything else in it
            # (token usage, other parts) - a brand new LlmResponse would drop that.
            part.text = part.text + " 🤖"
            print("✨ Added robot emoji to response!")
            return llm_response

    return None  # Nothing to modify (e.g. a tool call)


# Create a simple chatbot with model callbacks
# (LlmAgent is the full name of Agent - they are the same class)
root_agent = LlmAgent(
    name="filtered_chatbot",
    model=AGENT_MODEL,
    description="A chatbot that blocks profanity and adds emojis",
    instruction="""
    You are a friendly chatbot.
    - Be helpful and conversational
    - Keep responses short and friendly
    - Answer questions about various topics
    """,
    before_model_callback=before_model_callback,
    after_model_callback=after_model_callback,
)
