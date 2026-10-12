"""
LangGraph Core Concepts - Message State (Common Pattern)
add_messages reducer for chat-style graphs
"""

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END, add_messages
from typing_extensions import TypedDict, Annotated
from langchain_core.messages import HumanMessage, BaseMessage
from dotenv import load_dotenv

load_dotenv()


# === Message State (Common Pattern) ===


class MessageState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def demo_message_state():
    llm = init_chat_model("gpt-4o-mini", temperature=0)

    def chat_node(state: MessageState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(MessageState)
    graph.add_node("chat_node", chat_node)
    graph.add_edge(START, "chat_node")
    graph.add_edge("chat_node", END)

    app = graph.compile()

    result = app.invoke({"messages": [HumanMessage(content="Say Hello in Georgian")]})

    print("\nMessage State Result:")
    for msg in result["messages"]:
        role = "Human" if isinstance(msg, HumanMessage) else "AI"
        print(f"  {role}: {msg.content}")


if __name__ == "__main__":
    # go to .env LANGSMITH_TRACING=false to disable langsmith tracing, or set it to true to see the tracing in action
    demo_message_state()
