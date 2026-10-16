"""
Google ADK - 3. SequentialAgent (a fixed pipeline of agents)
Three agents run one after another: research -> itinerary -> optimization.

Run from the "12. ADK" folder:
    adk web                      (then pick agent_3_sequential in the dropdown)
    adk run agent_3_sequential   (chat in the terminal)

Needs GOOGLE_API_KEY in the .env file at the repo root.
"""

from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import google_search

load_dotenv()

# "gemini-flash-latest" always points to the current Flash model - pinned
# versions (e.g. "gemini-2.0-flash") get retired and start returning 404s
AGENT_MODEL = "gemini-flash-latest"


# Step 1: Destination Research Agent - researches location information.
# google_search is a built-in ADK tool (Gemini-only) that searches the web.
destination_research_agent = Agent(
    name="DestinationResearchAgent",
    model=AGENT_MODEL,
    tools=[google_search],
    description="An agent that researches travel destinations and gathers essential information",
    instruction="""
    You are a travel researcher. You will be given a destination and travel preferences, and you will research:
    - Best time to visit and weather patterns
    - Top attractions and must-see locations
    - Local culture, customs, and etiquette tips
    - Transportation options within the destination
    - Safety considerations and travel requirements
    Provide comprehensive destination insights for trip planning.
    """,
    # output_key saves this agent's final answer into the shared session state
    # under "destination_research", so the next agents can read it
    output_key="destination_research",
)


# Step 2: Itinerary Builder Agent - creates a detailed travel schedule.
# {destination_research} in the instruction is replaced with the value from
# session state before the prompt is sent to the LLM.
itinerary_builder_agent = Agent(
    model=AGENT_MODEL,
    name="ItineraryBuilderAgent",
    description="An agent that creates structured travel itineraries with daily schedules",
    instruction="""
    You are a professional travel planner. Using the research below, create a detailed itinerary that includes:
    - Day-by-day schedule with recommended activities
    - Suggested accommodation areas or districts
    - Estimated time requirements for each activity
    - Meal recommendations and dining suggestions
    - Budget estimates for major expenses
    Structure it logically for easy following during the trip.

    RESEARCH:
    {destination_research}
    """,
    output_key="travel_itinerary",
)

# Step 3: Travel Optimizer Agent - adds practical tips and optimizations
travel_optimizer_agent = Agent(
    model=AGENT_MODEL,
    name="TravelOptimizerAgent",
    description="An agent that optimizes travel plans with practical advice and alternatives",
    instruction="""
    You are a seasoned travel consultant. Using the itinerary from "travel_itinerary" output, optimize it by adding:
    - Money-saving tips and budget alternatives
    - Packing recommendations specific to the destination
    - Backup plans for weather or unexpected situations
    - Local apps, websites, or resources to download
    - Cultural do's and don'ts for respectful travel

    Format the final output as:

    ITINERARY: {travel_itinerary}

    OPTIMIZATION TIPS: [your money-saving and practical tips here]

    TRAVEL ESSENTIALS: [packing and preparation advice here]

    BACKUP PLANS: [alternative options and contingencies here]
    """,
)

# A SequentialAgent has no model, instruction or tools of its own - it is not an
# LLM. It only runs its sub_agents in the given order, every time.
root_agent = SequentialAgent(
    name="TravelPlanningSystem",
    description="A comprehensive system that researches destinations, builds itineraries, and optimizes travel plans",
    sub_agents=[
        destination_research_agent,
        itinerary_builder_agent,
        travel_optimizer_agent,
    ],
)
