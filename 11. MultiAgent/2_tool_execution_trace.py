"""
Tool-Calling Agents with LangGraph - Execution Trace
Step through every message the agent produces
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
from typing import Literal
from dotenv import load_dotenv
import os
import requests

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


@tool
def calculate(expression: str) -> str:
    """Calculate a mathematical expression. Example: calculate('2 + 2')"""
    try:
        result = eval(expression)  # Note: In production, use a safe math parser
        return f"The result of {expression} is {result}"
    except Exception as e:
        return f"Error calculating: {e}"


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    # Live data from OpenWeatherMap (needs OPENWEATHER_API_KEY in .env)
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Weather service unavailable: OPENWEATHER_API_KEY is not set"

    try:
        response = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city, "appid": api_key, "units": "metric"},  # metric = °C
            timeout=10,
        )
    except requests.RequestException as e:
        return f"Weather service error: {e}"

    # Errors go back to the LLM as text, so it can explain them instead of crashing
    if response.status_code == 404:
        return f"Weather data not available for {city}"
    if response.status_code != 200:
        try:
            message = response.json().get("message", "")
        except ValueError:
            message = response.text[:200]
        return f"Weather service error ({response.status_code}): {message}"

    data = response.json()
    temp = round(data["main"]["temp"])
    description = data["weather"][0]["description"].capitalize()
    return f"Weather in {city}: {temp}°C, {description}"


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def create_tool_agent():
    """Create a basic tool-calling agent."""

    tools = [calculate, get_weather]
    llm_with_tools = llm.bind_tools(tools)  # this is the secret!

    def agent_node(state: AgentState) -> dict:
        # Generate a response using the LLM with tool access
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        """Check if we should continue to tools or end."""
        last_message = state["messages"][-1]

        # If no tool calls, we're done
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return "end"
        return "tools"

    # create tool node
    tool_node = ToolNode(tools)

    # create graph
    graph = StateGraph(AgentState)

    # add nodes and edges
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)

    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", "end": END}
    )

    graph.add_edge("tools", "agent")  # loop back after tool execution

    return graph.compile()


def demo_tool_execution_trace():
    """Show detailed tool execution trace."""

    agent = create_tool_agent()

    print("\nTool Execution Trace:\n")

    result = agent.invoke(
        {
            "messages": [
                HumanMessage(content="Calculate 15% of 250 and check weather in Paris")
            ]
        }
    )

    for i, msg in enumerate(result["messages"]):
        msg_type = type(msg).__name__
        print(f"\n[{i}] {msg_type}:")

        if isinstance(msg, HumanMessage):
            print(f"  Content: {msg.content}")

        elif isinstance(msg, AIMessage):
            if msg.tool_calls:
                print(f"  Tool calls: {len(msg.tool_calls)}")
                for tc in msg.tool_calls:
                    print(f"    - {tc['name']}({tc['args']})")
            else:
                print(f"  Content: {msg.content}")

        elif isinstance(msg, ToolMessage):
            print(f"  Tool: {msg.name}")
            print(f"  Result: {msg.content}")


if __name__ == "__main__":
    demo_tool_execution_trace()
