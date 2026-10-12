"""
Checkpointing and Persistence in LangGraph - Branching Conversations
Fork a conversation into separate threads from a checkpoint
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


def demo_branching_conversations():
    """Branch conversations from checkpoints."""

    def chat(state: ChatState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("chat", chat)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)

    print("\nBranching Conversations Demo:\n")

    # Main conversation
    main_config: RunnableConfig = {"configurable": {"thread_id": "main"}}
    app.invoke(
        {"messages": [HumanMessage(content="What's the weather like?")]}, main_config
    )

    # Get checkpoint to branch from
    main_state = app.get_state(main_config)

    # Branch A - Beach vacation
    # A branch is just a NEW thread_id seeded with a copy of the main thread's state.
    branch_a_config: RunnableConfig = {"configurable": {"thread_id": "branch-beach"}}
    # Copy state to new thread
    app.update_state(branch_a_config, main_state.values)

    # Continues from the copied history, but only inside "branch-beach";
    # the "main" thread is untouched.

    result_a = app.invoke(
        {"messages": [HumanMessage(content="What about a beach vacation?")]},
        branch_a_config,
    )
    print(f"Branch A (Beach): {result_a['messages'][-1].content[:100]}...")

    # Branch B - Mountain adventure
    # Same starting point, different thread: B never sees A's beach messages.
    branch_b_config: RunnableConfig = {"configurable": {"thread_id": "branch-mountain"}}
    app.update_state(branch_b_config, main_state.values)

    result_b = app.invoke(
        {"messages": [HumanMessage(content="What about mountain hiking?")]},
        branch_b_config,
    )
    print(f"Branch B (Mountain): {result_b['messages'][-1].content[:100]}...")


if __name__ == "__main__":
    demo_branching_conversations()
