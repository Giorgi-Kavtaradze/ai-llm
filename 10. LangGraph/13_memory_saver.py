"""
Checkpointing and Persistence in LangGraph - Memory Saver
In-memory checkpointing for multi-turn conversations
"""

from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


# add_messages APPENDS new messages instead of replacing the list, so the history
# grows with every turn. It also gives each message an ID, so re-sending a message
# updates it rather than duplicating it.
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def demo_memory_saver():
    """In-memory checkpointing for development."""

    def chat(state: ChatState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(ChatState)

    graph.add_node("chat", chat)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    # The checkpointer saves state after every step. MemorySaver keeps it in RAM,
    # so it's lost when the program exits (fine for development).
    saver = MemorySaver()
    app = graph.compile(checkpointer=saver)

    # Configuration with thread_id
    # thread_id = one conversation. Same thread_id -> LangGraph loads that thread's saved state.
    config: RunnableConfig = {"configurable": {"thread_id": "user-123"}}

    print("Memory Saver Demo (Multi-turn conversation):\n")

    # Turn 1
    result = app.invoke(
        {"messages": [HumanMessage(content="My name is Tornike")]}, config
    )
    print(f"Turn 1 - AI: {result['messages'][-1].content}")

    # Turn 2 - Conversation continues
    # We only send the NEW message. The checkpointer restores turn 1 and the
    # reducer appends to it, so the LLM sees the whole conversation.
    result = app.invoke({"messages": [HumanMessage(content="What's my name?")]}, config)
    print(f"Turn 2 - AI: {result['messages'][-1].content}")

    # Check full history
    # 4 messages = 2 human + 2 AI, all stored in the checkpoint
    state = app.get_state(config)
    print(f"\nTotal messages in state: {len(state.values['messages'])}")


if __name__ == "__main__":
    demo_memory_saver()
