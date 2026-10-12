"""
Checkpointing and Persistence in LangGraph - SQLite Persistence
Durable checkpoints that survive an app restart
"""

from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from typing_extensions import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
import tempfile
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


# add_messages APPENDS new messages instead of replacing the list, so the history
# grows with every turn. It also gives each message an ID, so re-sending a message
# updates it rather than duplicating it.
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def demo_sqlite_persistence():
    """SQLite persistence for durable storage."""

    def chat(state: ChatState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("chat", chat)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)

    # Create temp database
    # Checkpoints now go to a file on disk, so they survive the program restarting.
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    print(f"\nSQLite Persistence Demo:")
    print(f"Database: {db_path}\n")

    # First session
    # SqliteSaver opens a DB connection; the `with` block closes it at the end,
    # like shutting the app down.
    with SqliteSaver.from_conn_string(db_path) as saver:
        app = graph.compile(checkpointer=saver)
        config: RunnableConfig = {"configurable": {"thread_id": "persistent-user"}}

        result = app.invoke(
            {
                "messages": [
                    HumanMessage(content="Remember: The secret code is ALPHA-7")
                ]
            },
            config,
        )
        print(f"Session 1 - Stored secret code")

        # PostgresSaver with a real database!
        # Simulate app restart - new session
    # New connection + newly compiled graph: nothing is in memory any more.
    # The same thread_id loads session 1's messages back from the SQLite file.
    with SqliteSaver.from_conn_string(db_path) as saver:
        app = graph.compile(checkpointer=saver)
        config: RunnableConfig = {"configurable": {"thread_id": "persistent-user"}}

        result = app.invoke(
            {"messages": [HumanMessage(content="What was the secret code?")]}, config
        )
        print(f"Session 2 - AI: {result['messages'][-1].content}")


if __name__ == "__main__":
    demo_sqlite_persistence()
