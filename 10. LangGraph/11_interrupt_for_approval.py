"""
Human-in-the-Loop Patterns in LangGraph - Interrupt for Approval
Interrupt, review, modify, and resume
"""

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableConfig
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ─── Helper for visual separation ───
def phase_banner(phase_num: int, title: str):
    print(f"\n{'=' * 55}")
    print(f"  PHASE {phase_num}: {title}")
    print(f"{'=' * 55}")


def step_print(icon: str, label: str, detail: str = ""):
    print(f"\n{icon} [{label}] {detail}")


# ════════════════════════════════════════════════════════
# DEMO 1: Interrupt for Approval
# ════════════════════════════════════════════════════════


# Shared state: every node reads from it and returns updates to it.
# `approved` and `feedback` are the fields the HUMAN fills in while the graph is paused.
class ApprovalState(TypedDict):
    request: str  # what the user asked for
    draft: str  # LLM's first attempt
    approved: bool  # human decision
    feedback: str  # human's requested changes
    final: str  # output after human review


def demo_interrupt_for_approval():
    """Interrupt execution for human approval."""

    # Node 1: LLM writes a draft. Runs BEFORE the pause.
    def create_draft(state: ApprovalState) -> dict:
        step_print("📝", "DRAFT NODE", "Entering create_draft node...")
        print(f"   Request: \"{state['request']}\"")
        print(f"   Calling LLM to generate draft...")

        response = llm.invoke(f"Create a professional response for: {state['request']}")

        print(f"   Draft generated ({len(response.content.split())} words)")  # type: ignore
        print(f"   Preview: {response.content[:100]}...")
        return {"draft": response.content}

    # Node 2: the checkpoint the graph pauses in front of. It does no work itself;
    # by the time it runs, the human's input is already in the state.
    def wait_for_approval(state: ApprovalState) -> dict:
        step_print("👁️", "APPROVAL NODE", "Entering wait_for_approval node...")
        print(f"   Approved: {state['approved']}")
        print(
            f"   Feedback: '{state['feedback']}'"
            if state["feedback"]
            else "   Feedback: (none yet)"
        )
        # This node is where we'll interrupt
        return state  # type: ignore

    # Node 3: acts on the human's decision (use the draft, or revise it with the feedback).
    def finalize(state: ApprovalState) -> dict:
        step_print("📦", "FINALIZE NODE", "Entering finalize node...")
        print(f"   Approved: {state['approved']}")

        if state["approved"]:
            print(f"   Action: Using draft as-is (human approved)")
            return {"final": state["draft"]}
        else:
            print(f"   Action: Revising draft based on feedback...")
            print(f"   Feedback: \"{state['feedback']}\"")
            # Incorporate feedback
            response = llm.invoke(
                f"Revise this draft based on feedback:\n\n"
                f"Draft: {state['draft']}\n\n"
                f"Feedback: {state['feedback']}"
            )
            print(f"   Revised draft generated ({len(response.content.split())} words)")  # type: ignore
            return {"final": response.content}

    # Straight line: draft -> approval -> finalize. The "human" part comes from the interrupt, not the edges.
    graph = StateGraph(ApprovalState)

    graph.add_node("draft", create_draft)
    graph.add_node("approval", wait_for_approval)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "draft")
    graph.add_edge("draft", "approval")
    graph.add_edge("approval", "finalize")
    graph.add_edge("finalize", END)

    # Compile with checkpointer and interrupt
    # - checkpointer: saves the state after every step, so a paused graph can be resumed later
    #   (MemorySaver keeps it in RAM; production would use a database-backed saver)
    # - interrupt_before: stop right before "approval" runs and hand control back to our code
    memory = MemorySaver()
    app = graph.compile(
        checkpointer=memory, interrupt_before=["approval"]  # Pause before this node
    )

    print("\n" + "=" * 55)
    print("  HUMAN-IN-THE-LOOP: APPROVAL WORKFLOW")
    print("=" * 55)

    print("\n   Graph: START -> [draft] -> ⏸️ -> [approval] -> [finalize] -> END")
    print("   Interrupt set BEFORE: 'approval' node")

    # Configuration for this thread
    # thread_id identifies this conversation's saved state. Every call below must pass the
    # same config, so LangGraph knows which checkpoint to read, update, or resume.
    config: RunnableConfig = {"configurable": {"thread_id": "demo-1"}}

    # ─── PHASE 1: Run until interrupt ───
    phase_banner(1, "RUN UNTIL INTERRUPT")
    print("   Calling app.invoke() with initial state...")
    print("   The graph will run until it hits the interrupt point.\n")

    # Runs START -> draft, then stops before "approval". invoke() returns the state so far.
    result = app.invoke(
        {
            "request": "Write a thank-you email for a job interview",
            "draft": "",
            "approved": False,
            "feedback": "",
            "final": "",
        },
        config,
    )

    step_print("⏸️", "PAUSED", "Graph execution interrupted!")
    print(f"   Draft is ready: {result['draft'][:150]}...")
    print(f"   Final is empty: '{result['final']}'")
    print(f"\n   The graph is now FROZEN. Waiting for human input.")
    print(f"   In a real app, your frontend would show the draft here.")

    # ─── PHASE 2: Inspect paused state ───
    phase_banner(2, "INSPECT PAUSED STATE")

    # get_state() reads the saved checkpoint without running anything.
    # .values = the state, .next = which node(s) will run on resume.
    current_state = app.get_state(config)
    print(f"   app.get_state(config) tells us:")
    print(f"   Next node(s): {current_state.next}")
    print(f"   State keys: {list(current_state.values.keys())}")
    print(f"   Draft filled: {'Yes' if current_state.values['draft'] else 'No'}")
    print(f"   Approved: {current_state.values['approved']}")
    print(f"   Final filled: {'Yes' if current_state.values['final'] else 'No'}")

    # ─── PHASE 3: Human provides feedback and resume ───
    phase_banner(3, "HUMAN INJECTS FEEDBACK + RESUME")

    feedback_text = (
        "Make it more concise and add specific mention of the company culture"
    )
    print(f"   Human decision: REJECT (request changes)")
    print(f'   Human feedback: "{feedback_text}"')
    print(f"\n   Calling app.update_state() to inject human input...")

    # Update state with human input
    # update_state() edits the paused checkpoint, as if a node had returned these values.
    # In a real app this is where your UI's "Approve" / "Request changes" button lands.
    app.update_state(
        config, {"approved": False, "feedback": feedback_text}  # Request changes
    )

    print(f"   State updated. approved=False, feedback set.")
    print(f"\n   Calling app.invoke(None, config) to RESUME...")
    print(f"   (None means 'no new input, just continue from checkpoint')\n")

    # Continue execution
    # invoke(None, config) = "no new input, resume this thread from its checkpoint".
    # Runs approval -> finalize -> END, now seeing the human's feedback.
    final_result = app.invoke(None, config)

    # ─── RESULT ───
    step_print("✅", "WORKFLOW COMPLETE", "")
    print(f"   Final result ({len(final_result['final'].split())} words):")
    print(f"   {final_result['final'][:200]}...")
    print(f"\n   Graph path taken:")
    print(
        f"   START -> [draft] -> ⏸️ PAUSE -> human feedback -> [approval] -> [finalize] -> END"
    )


if __name__ == "__main__":
    demo_interrupt_for_approval()
