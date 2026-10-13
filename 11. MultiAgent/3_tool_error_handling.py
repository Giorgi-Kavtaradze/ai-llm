"""
Tool-Calling Agents with LangGraph - Tool Error Handling
Tools that return errors the LLM can explain
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


@tool
def divide(a: float, b: float) -> str:
    """Divide two numbers."""
    if b == 0:
        return "Error: Division by zero"
    result = a / b
    return f"The result of {a} divided by {b} is {result}"


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def demo_tool_with_errors():
    """Demo tool error handling."""

    tools = [divide]
    llm_with_tools = llm.bind_tools(tools)

    def agent_node(state: AgentState) -> dict:
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def should_continue(state: AgentState) -> Literal["tools", "end"]:
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            return "end"
        return "tools"

    tool_node = ToolNode(tools)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent", should_continue, {"tools": "tools", "end": END}
    )
    graph.add_edge("tools", "agent")

    agent = graph.compile()

    print("\nTool Error Handling Demo:\n")

    queries = [
        "Divide 100 by 5",
        "Divide 100 by 0",  # Will trigger error
    ]

    for query in queries:
        result = agent.invoke({"messages": [HumanMessage(content=query)]})
        print(f"Query: {query}")
        print(f"Response: {result['messages'][-1].content}")
        print("-" * 40)


if __name__ == "__main__":
    demo_tool_with_errors()
