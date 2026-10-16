"""
Google ADK - 2. Agent with Gemini + tools
The same travel planner, now on Gemini and with two Python functions as tools.

Run from the "12. ADK" folder:
    adk web                        (then pick agent_2_gemini_tools in the dropdown)
    adk run agent_2_gemini_tools   (chat in the terminal)

Needs GOOGLE_API_KEY and OPENWEATHER_API_KEY in the .env file at the repo root.
"""

import datetime
import os
import requests
from dotenv import load_dotenv
from google.adk.agents import Agent

load_dotenv()  # GOOGLE_API_KEY is picked up from the environment automatically

# Gemini models are supported natively, so no LiteLlm wrapper is needed here -
# just pass the model name as a string
# "gemini-flash-latest" always points to the current Flash model - pinned
# versions (e.g. "gemini-2.0-flash") get retired and start returning 404s
AGENT_MODEL = "gemini-flash-latest"


# --- Tools ---
# In ADK a tool is just a Python function. ADK reads the name, type hints and
# docstring and shows them to the LLM, so the docstring is what tells the model
# when and how to call the tool. Returning a dict with a "status" key lets the
# model tell success from failure.

# Helper, not a tool: it is not in the agent's tools list, so the LLM never sees it
def fetch_city_weather(city: str) -> tuple[dict | None, dict | None]:
    """Calls OpenWeatherMap for a city. Returns (data, None) or (None, error dict)."""
    # Live data from OpenWeatherMap (needs OPENWEATHER_API_KEY in .env)
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return None, {
            "status": "error",
            "error_message": "Weather service unavailable: OPENWEATHER_API_KEY is not set.",
        }

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"},  # metric = °C
            timeout=10,
        )
    except requests.RequestException as e:
        return None, {"status": "error", "error_message": f"Weather service error: {e}"}

    # Errors go back to the LLM in the dict, so it can explain them instead of crashing
    if response.status_code == 404:
        return None, {
            "status": "error",
            "error_message": f"Sorry, I couldn't find a city called '{city}'.",
        }
    if response.status_code != 200:
        try:
            message = response.json().get("message", "")
        except ValueError:
            message = response.text[:200]
        return None, {
            "status": "error",
            "error_message": f"Weather service error ({response.status_code}): {message}",
        }

    return response.json(), None


def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").

    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for city: {city} ---")  # Log tool execution

    data, error = fetch_city_weather(city)
    if error:
        return error

    temp = round(data["main"]["temp"]) # type: ignore
    description = data["weather"][0]["description"] # type: ignore
    print(f"API response - Weather in {city}: {temp}°C, {description}")
    return {
        "status": "success",
        "report": f"The weather in {city} is {description} with a temperature of {temp}°C.",
    }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """
    print(f"--- Tool: get_current_time called for city: {city} ---")  # Log tool execution

    # OpenWeatherMap also returns the city's UTC offset in seconds ("timezone")
    data, error = fetch_city_weather(city)
    if error:
        return error

    tz = datetime.timezone(datetime.timedelta(seconds=data["timezone"])) # type: ignore
    now = datetime.datetime.now(tz)
    report = f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S UTC%z")}'
    print(f"API response - {report}")
    return {"status": "success", "report": report}


root_agent = Agent(
    name="TravelPlannerAgent",
    model=AGENT_MODEL,
    description="A travel planner agent that helps users plan their trips",
    instruction="""
    You are a friendly travel planner. Help the user plan their trip:
    suggest things to do, places to stay and a rough day-by-day plan.
    Use get_weather for the current weather and get_current_time for the
    local time in a city - never guess them.
    """,
    # The agent decides on its own when to call these
    tools=[get_weather, get_current_time],
)
