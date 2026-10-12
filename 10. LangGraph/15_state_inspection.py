"""
Checkpointing and Persistence in LangGraph - State Inspection
Read the current state and checkpoint history
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


def demo_state_inspection():
    """Inspect and manipulate checkpoint state."""

    def chat(state: ChatState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("chat", chat)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)
    config: RunnableConfig = {"configurable": {"thread_id": "inspect-demo"}}

    print("\nState Inspection Demo:\n")

    # Build up some state
    app.invoke({"messages": [HumanMessage(content="Hello!")]}, config)
    app.invoke({"messages": [HumanMessage(content="How are you?")]}, config)

    # Get current state
    # get_state() returns the LATEST checkpoint: .values is the data, .next is
    # the node(s) still to run (empty () when the graph has finished).
    state = app.get_state(config)

    print("Current state:")
    print(f"  Next node: {state.next}")
    print(f"  Message count: {len(state.values['messages'])}")

    # Get state history
    # get_state_history() returns EVERY checkpoint of the thread, newest first.
    # Each invoke() adds several (input, start, after each node), which is why
    # the message counts step down.
    print("\nState history:")
    for i, snapshot in enumerate(app.get_state_history(config)):
        print(f"  Checkpoint {i}: {len(snapshot.values['messages'])} messages")
        if i >= 3:
            print("  ...")
            break


if __name__ == "__main__":
    demo_state_inspection()
