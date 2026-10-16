"""
Google ADK - 1. Basic Agent with a local Ollama model
A single travel planner agent, no tools yet.

Run from the "12. ADK" folder:
    adk web                  (then pick agent_1_ollama in the dropdown)
    adk run agent_1_ollama   (chat in the terminal)

Needs Ollama running locally with the model pulled: ollama pull gemma4
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

# ADK talks to Gemini natively. For any other provider we wrap the model in
# LiteLlm, which speaks to 100+ providers using "provider/model" names.
# "ollama_chat/" (not "ollama/") uses Ollama's chat API, which ADK recommends.
# Swap it to try other providers, e.g. LiteLlm("openai/gpt-4o-mini").
AGENT_MODEL = LiteLlm(model="ollama_chat/gemma4")

# ADK looks for a variable called `root_agent` - that is the agent it runs
root_agent = Agent(
    name="TravelPlannerAgent",  # must be a valid identifier (no spaces or hyphens)
    model=AGENT_MODEL,
    description="A travel planner agent that helps users plan their trips",
    # The instruction is the system prompt
    instruction="""
    You are a friendly travel planner. Help the user plan their trip:
    suggest things to do, places to stay and a rough day-by-day plan.
    Ask a short follow-up question if the destination or dates are unclear.
    """,
)
