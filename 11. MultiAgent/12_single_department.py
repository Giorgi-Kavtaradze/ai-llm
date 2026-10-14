"""
Hierarchical Agents in LangGraph - Single Department
One department subgraph (the Research Team) run on its own
"""

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from typing_extensions import TypedDict, Annotated
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ============================================================
# Shared state schema used across all levels
# ============================================================


class TeamState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    final_answer: str


# ============================================================
# Department 1: Research Team (subgraph)
# ============================================================


def build_research_team() -> StateGraph:
    """Build the research department subgraph."""

    def web_researcher(state: TeamState) -> dict:
        """Searches the web for information."""
        # Extract the query from the last human message
        query = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a web researcher. Find key facts and data about "
                        "the topic. Provide 3-4 bullet points of findings. Be specific."
                    )
                ),
                HumanMessage(content=query),
            ]
        )

        return {
            "messages": [
                AIMessage(
                    content=f"[WEB RESEARCHER]: {response.content}",
                    name="web_researcher",
                )
            ]
        }

    def paper_reviewer(state: TeamState) -> dict:
        """Reviews academic/technical sources."""
        query = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                query = msg.content
                break

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are an academic reviewer. Provide technical depth and "
                        "cite relevant concepts or frameworks. 3-4 bullet points."
                    )
                ),
                HumanMessage(content=query),
            ]
        )

        return {
            "messages": [
                AIMessage(
                    content=f"[PAPER REVIEWER]: {response.content}",
                    name="paper_reviewer",
                )
            ]
        }

    def research_lead(state: TeamState) -> dict:
        """Synthesizes findings from both researchers."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are the research lead. Synthesize the web researcher's "
                        "and paper reviewer's findings into a cohesive research brief. "
                        "Keep it to one short paragraph."
                    )
                ),
                *state["messages"],
            ]
        )

        return {
            "messages": [
                AIMessage(
                    content=f"[RESEARCH LEAD]: {response.content}", name="research_lead"
                )
            ],
            "final_answer": response.content,
        }

    # Build the research subgraph
    research_graph = StateGraph(TeamState)

    research_graph.add_node("web_researcher", web_researcher)
    research_graph.add_node("paper_reviewer", paper_reviewer)
    research_graph.add_node("research_lead", research_lead)

    # Fan-out: both researchers work in parallel
    research_graph.add_edge(START, "web_researcher")
    research_graph.add_edge(START, "paper_reviewer")

    # Fan-in: both feed into the research lead
    research_graph.add_edge("web_researcher", "research_lead")
    research_graph.add_edge("paper_reviewer", "research_lead")

    research_graph.add_edge("research_lead", END)

    return research_graph


def demo_single_department():
    """Demo a single department subgraph in isolation."""

    print("Single Department Demo (Research Team):\n")

    research_team = build_research_team().compile()

    result = research_team.invoke(
        {
            "messages": [
                HumanMessage(content="What is retrieval-augmented generation (RAG)?")
            ],
            "final_answer": "",
        }
    )

    for msg in result["messages"]:
        if isinstance(msg, AIMessage):
            print(f"{msg.content[:200]}...\n")

    print(f"Research Brief:\n{result['final_answer']}")


if __name__ == "__main__":
    demo_single_department()
