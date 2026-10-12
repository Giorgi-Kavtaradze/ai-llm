"""
Checkpointing and Persistence in LangGraph
Save and resume agent state
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from typing_extensions import TypedDict, Annotated
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
import operator
import tempfile
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)


# Shared by the first four demos. operator.add APPENDS new messages instead of
# replacing the list, so the history grows with every turn.
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


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
        {"messages": [HumanMessage(content="My name is Paulo")]}, config
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


def demo_checkpoint_internals():
    """
    Peek inside a checkpoint — see exactly what LangGraph saves.

    Uses a 2-node graph so we generate multiple checkpoints,
    then walks through every field in the checkpoint object.
    """

    # ── Build a 2-node graph so we get several checkpoints ──

    class TaskState(TypedDict):
        messages: Annotated[list[BaseMessage], operator.add]
        step: str

    def analyze(state: TaskState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response], "step": "analyzed"}

    def summarize(state: TaskState) -> dict:
        summary_prompt = [
            HumanMessage(
                content=f"Summarize this in one sentence: {state['messages'][-1].content}"
            )
        ]
        response = llm.invoke(summary_prompt)
        return {"messages": [response], "step": "summarized"}

    graph = StateGraph(TaskState)
    graph.add_node("analyze", analyze)
    graph.add_node("summarize", summarize)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "summarize")
    graph.add_edge("summarize", END)

    memory = MemorySaver()
    app = graph.compile(checkpointer=memory)
    config: RunnableConfig = {"configurable": {"thread_id": "internals-demo"}}

    print("\nCheckpoint Internals Demo")
    print("=" * 55)
    print("Graph: START -> [analyze] -> [summarize] -> END")
    print("=" * 55)

    # ── Run the graph ──
    # One invoke() saves 4 checkpoints: input, start, after analyze, after summarize

    app.invoke(
        {"messages": [HumanMessage(content="Explain why the sky is blue")], "step": ""},
        config,
    )

    # ════════════════════════════════════════════════════════
    # PART 1: What's in the CURRENT state snapshot?
    # ════════════════════════════════════════════════════════

    print("\n--- PART 1: Current State Snapshot (app.get_state) ---\n")

    state = app.get_state(config)

    # state.values — your actual TypedDict data
    print("1) state.values (your state data):")
    print(f"   step: '{state.values['step']}'")
    print(f"   messages: {len(state.values['messages'])} total")
    for i, msg in enumerate(state.values["messages"]):
        role = "Human" if isinstance(msg, HumanMessage) else "AI"
        print(f"     [{i}] {role}: {msg.content[:80]}...")

    # state.next — which node runs next (empty = graph finished)
    print(f"\n2) state.next (pending node):")
    print(f"   {state.next if state.next else '() — graph finished, no pending nodes'}")

    # state.config — the config that produced this snapshot
    print(f"\n3) state.config (thread + checkpoint IDs):")
    print(f"   thread_id:     {state.config['configurable']['thread_id']}")  # type: ignore
    print(f"   checkpoint_id: {state.config['configurable']['checkpoint_id']}")  # type: ignore

    # state.metadata — how this checkpoint was created
    # source: "input" = the initial invoke() input, "loop" = saved after a node ran,
    #         "update" = written by update_state()
    print(f"\n4) state.metadata (provenance info):")
    print(f"   source:  {state.metadata.get('source', 'N/A')}")  # type: ignore
    print(f"   step:    {state.metadata.get('step', 'N/A')}")  # type: ignore

    # state.parent_config — pointer to the PREVIOUS checkpoint
    print(f"\n5) state.parent_config (previous checkpoint):")
    if state.parent_config:
        print(
            f"   parent checkpoint_id: {state.parent_config['configurable']['checkpoint_id']}"  # type: ignore
        )
    else:
        print(f"   None — this is the very first checkpoint")

    # state.created_at — timestamp
    print(f"\n6) state.created_at (when saved):")
    print(f"   {state.created_at}")

    # ════════════════════════════════════════════════════════
    # PART 2: Walk through ALL checkpoints (time travel)
    # ════════════════════════════════════════════════════════

    print("\n--- PART 2: Full Checkpoint History (app.get_state_history) ---\n")
    print("LangGraph saves a checkpoint at EACH step. Let's see them all:\n")

    # History comes newest-first, so history[i + 1] is the parent of history[i]
    history = list(app.get_state_history(config))

    for i, snapshot in enumerate(history):
        step_num = snapshot.metadata.get("step", "?")  # type: ignore
        source = snapshot.metadata.get("source", "?")  # type: ignore
        msg_count = len(snapshot.values.get("messages", []))
        checkpoint_id = snapshot.config["configurable"]["checkpoint_id"]  # type: ignore
        current_step = snapshot.values.get("step", "")

        # Which node just wrote to this checkpoint?
        # The metadata doesn't record it, but the parent's .next does:
        # whatever the parent was about to run is what produced this checkpoint.
        parent = history[i + 1] if i + 1 < len(history) else None
        node_name = ", ".join(parent.next) if parent else "— (initial input)"

        print(f"  Checkpoint {i}:")
        print(f"    id:         {checkpoint_id[:30]}...")
        print(f"    source:     {source}")
        print(f"    step:       {step_num}")
        print(f"    written by: {node_name}")
        print(f"    state.step: '{current_step}'")
        print(f"    messages:   {msg_count}")
        print(f"    next:       {snapshot.next if snapshot.next else '() — finished'}")
        print(f"    created_at: {snapshot.created_at}")
        print()

    # ════════════════════════════════════════════════════════
    # PART 3: Jump to a specific checkpoint (rewind)
    # ════════════════════════════════════════════════════════

    print("--- PART 3: Rewind — Jump to a Previous Checkpoint ---\n")

    # Find the checkpoint right after the "analyze" node ran,
    # i.e. the one whose next node is "summarize"
    target_snapshot = None
    for snapshot in app.get_state_history(config):
        if snapshot.next == ("summarize",):
            target_snapshot = snapshot
            break

    if target_snapshot:
        target_id = target_snapshot.config["configurable"]["checkpoint_id"]  # type: ignore
        print(f"  Found checkpoint after 'analyze' node: {target_id[:30]}...")
        print(f"  Messages at that point: {len(target_snapshot.values['messages'])}")
        print(f"  state.step at that point: '{target_snapshot.values.get('step', '')}'")

        # You can resume from this exact checkpoint
        # Adding checkpoint_id to the config points at that snapshot instead of the latest one.
        rewind_config: RunnableConfig = {
            "configurable": {"thread_id": "internals-demo", "checkpoint_id": target_id}
        }

        rewound_state = app.get_state(rewind_config)
        print(f"\n  Loaded checkpoint — next node would be: {rewound_state.next}")
        print(f"  We're back to BEFORE 'summarize' ran!")
        print(
            f"  Calling invoke(None) from here would re-run 'summarize' with fresh output."
        )
    else:
        print("  Could not find target checkpoint.")

    # ════════════════════════════════════════════════════════
    # SUMMARY: Anatomy of a checkpoint
    # ════════════════════════════════════════════════════════

    print("\n" + "=" * 55)
    print("  CHECKPOINT ANATOMY — What Gets Saved")
    print("=" * 55)
    print(
        """
    state.values        → Your TypedDict data (messages, step, etc.)
    state.next          → Tuple of nodes that run next (() if done)
    state.config        → thread_id + checkpoint_id (unique address)
    state.parent_config → Previous checkpoint's address (linked list)
    state.metadata      → source (input / loop / update) and step number
    state.created_at    → Timestamp of when this checkpoint was saved

    Checkpoints are saved:
      1. BEFORE the first node runs (initial input state)
      2. AFTER each node completes (with updated state)
      3. At interrupt points (frozen state for human-in-the-loop)

    Think of it as a linked list of snapshots:
      [initial] --> [after analyze] --> [after summarize]
         ^               ^                    ^
       parent          parent              current (latest)
    """
    )


if __name__ == "__main__":
    # Uncomment one demo at a time
    # demo_memory_saver()
    # demo_sqlite_persistence()
    # demo_state_inspection()
    # demo_branching_conversations()
    demo_checkpoint_internals()
