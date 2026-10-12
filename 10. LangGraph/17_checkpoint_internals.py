"""
Checkpointing and Persistence in LangGraph - Checkpoint Internals
See exactly what LangGraph saves, and rewind to an earlier checkpoint
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


def demo_checkpoint_internals():
    """
    Peek inside a checkpoint — see exactly what LangGraph saves.

    Uses a 2-node graph so we generate multiple checkpoints,
    then walks through every field in the checkpoint object.
    """

    # ── Build a 2-node graph so we get several checkpoints ──

    class TaskState(TypedDict):
        messages: Annotated[list[BaseMessage], add_messages]
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
    demo_checkpoint_internals()
