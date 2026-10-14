"""
Agent Communication Patterns in LangGraph - Blackboard Pattern
Combines shared workspace + messages + iterative refinement
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
from typing import Literal
from pydantic import BaseModel, Field
import operator
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# Blackboard: agents take turns refining one shared workspace (the "board").
#   - Agents read and write board FIELDS, like 10_shared_state.py, but they come back
#     to the same board again and again instead of each filling in its section once
#   - The board decides what runs next: the router checks is_approved, not a fixed order
#   - Context stays small: each turn sends only the topic + latest draft + latest feedback
#   - drafts/critiques keep every version, so you can see how the text evolved
# Compare with 9_message_passing.py, where agents read the whole conversation.


class BlackboardState(TypedDict):
    # Log only: agents never READ this, it just records what happened for printing.
    # The real communication happens through the board fields below.
    messages: Annotated[list[BaseMessage], add_messages]
    # Blackboard fields — the shared workspace
    topic: str
    drafts: Annotated[list[str], operator.add]  # every version, newest last
    critiques: Annotated[list[str], operator.add]  # feedback for each rejected draft
    iteration: int
    is_approved: bool


def create_blackboard_system():
    """
    Blackboard pattern: multiple agents read/write a shared workspace.
    A drafter writes, a critic reviews, and they iterate until approved.
    """

    class ApprovalDecision(BaseModel):
        approved: bool = Field(description="Whether the draft is good enough")
        feedback: str = Field(
            description="Concrete improvements to make, or why the draft is approved"
        )

    critic_llm = llm.with_structured_output(ApprovalDecision)

    def drafter(state: BlackboardState) -> dict:
        """Reads critiques from blackboard, writes improved draft."""
        context_parts = [f"Topic: {state['topic']}"]

        if state["drafts"]:
            context_parts.append(f"Previous draft: {state['drafts'][-1]}")
        if state["critiques"]:
            context_parts.append(f"Feedback to address: {state['critiques'][-1]}")

        context = "\n".join(context_parts)

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a skilled writer. Write or revise a short paragraph "
                        "(3-4 sentences) based on the topic and any feedback provided. "
                        "If there's feedback, directly address it in your revision."
                    )
                ),
                HumanMessage(content=context),
            ]
        )

        return {
            "drafts": [response.text],
            "messages": [
                AIMessage(
                    content=f"[DRAFTER iteration {state['iteration'] + 1}]: {response.text}",
                    name="drafter",
                )
            ],
            "iteration": state["iteration"] + 1,
        }

    def critic(state: BlackboardState) -> dict:
        """Reads latest draft from blackboard, writes critique or approves."""
        latest_draft = state["drafts"][-1] if state["drafts"] else "No draft yet"

        decision: ApprovalDecision = critic_llm.invoke(  # type: ignore
            [
                SystemMessage(
                    content=(
                        "You are a strict editor. Review the draft for clarity, accuracy, "
                        "and engagement. Approve ONLY if it's genuinely good. "
                        "Always give concrete, specific feedback. "
                        "If iteration is 3 or more, be more lenient."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Topic: {state['topic']}\n"
                        f"Iteration: {state['iteration']}\n"
                        f"Draft: {latest_draft}"
                    )
                ),
            ]
        )

        # Never approve the first draft, so the demo always shows at least one revision.
        # Force approval after 3 iterations to prevent infinite loops.
        iteration = state["iteration"]
        approved = (decision.approved and iteration >= 2) or iteration >= 3

        result = {
            "is_approved": approved,
            "messages": [
                AIMessage(
                    content=f"[CRITIC]: {'APPROVED' if approved else 'REVISION NEEDED'} - {decision.feedback}",
                    name="critic",
                )
            ],
        }

        if not approved:
            result["critiques"] = [decision.feedback]

        return result

    def route_after_critic(state: BlackboardState) -> Literal["drafter", "end"]:
        """Loop back to drafter if not approved."""
        if state["is_approved"]:
            return "end"
        return "drafter"

    graph = StateGraph(BlackboardState)

    graph.add_node("drafter", drafter)
    graph.add_node("critic", critic)

    graph.add_edge(START, "drafter")
    graph.add_edge("drafter", "critic")
    graph.add_conditional_edges(
        "critic", route_after_critic, {"drafter": "drafter", "end": END}
    )

    return graph.compile()


def demo_blackboard():
    """Demo blackboard iterative refinement."""
    agent = create_blackboard_system()

    print("Blackboard Pattern Demo:\n")

    result = agent.invoke(
        {
            "messages": [],
            "topic": "Why LangGraph is great for building multi-agent systems",
            "drafts": [],
            "critiques": [],
            "iteration": 0,
            "is_approved": False,
        }
    )

    print(f"Total iterations: {result['iteration']}")
    print(f"Approved: {result['is_approved']}")

    print("\nConversation:")
    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"\n{msg.content}")

    print(f"\nFinal draft:\n{result['drafts'][-1]}")


if __name__ == "__main__":
    demo_blackboard()
