"""
Parallel Agent Execution in LangGraph - Map-Reduce
Summarize several documents in parallel, then combine the summaries
"""

from langgraph.graph import StateGraph, START, END
from langgraph.types import Send
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing_extensions import TypedDict, Annotated
import operator
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


# Map-Reduce Pattern
#   MAP:    split the work into independent pieces and process them in parallel
#   REDUCE: combine the partial results into one answer
#
# Unlike 7_parallel_agents.py, where the 3 parallel branches are fixed in the graph,
# here the number of branches is decided at RUNTIME: one per document.


# Main graph state
class MapReduceState(TypedDict):
    documents: list[str]
    # Each parallel branch returns ONE summary. operator.add appends them all into
    # this list. Without a reducer, the branches would overwrite each other.
    summaries: Annotated[list[str], operator.add]
    final_summary: str


# State for ONE map branch: it only needs its own document, not the whole graph state
class DocState(TypedDict):
    doc: str


def create_map_reduce_summarizer():
    """Summarize multiple documents in parallel."""

    # Fan-out: called on the edge out of START.
    # Each Send("summarize", {...}) starts a separate copy of the "summarize" node
    # with its own input. 3 documents -> 3 copies, all running at the same time.
    def fan_out(state: MapReduceState) -> list[Send]:
        return [Send("summarize", {"doc": doc}) for doc in state["documents"]]

    # MAP step: summarizes a single document. Runs once per Send, in parallel.
    def summarize_doc(state: DocState) -> dict:
        print(f"  [map] start:  {state['doc'][:40]}...")
        response = llm.invoke(
            [
                SystemMessage(content="Summarize this document in 2-3 sentences."),
                HumanMessage(content=state["doc"]),
            ]
        )
        print(f"  [map] done:   {state['doc'][:40]}...")
        # Return a one-item list; the operator.add reducer merges all branches' lists
        return {"summaries": [response.content]}

    # REDUCE step: runs once, after ALL map branches have finished
    def reduce_combine(state: MapReduceState) -> dict:
        """Combine all summaries."""
        all_summaries = "\n\n".join(
            [f"Summary {i+1}: {s}" for i, s in enumerate(state["summaries"])]
        )

        response = llm.invoke(
            [
                SystemMessage(
                    content="Combine these summaries into one coherent overview."
                ),
                HumanMessage(content=all_summaries),
            ]
        )
        return {"final_summary": response.content}

    graph = StateGraph(MapReduceState)
    graph.add_node("summarize", summarize_doc)
    graph.add_node("reduce", reduce_combine)

    # Conditional edge that returns Send objects instead of a node name.
    # ["summarize"] lists the possible targets (used for validation and drawing the graph).
    graph.add_conditional_edges(START, fan_out, ["summarize"])
    # LangGraph waits for every "summarize" branch before running "reduce"
    graph.add_edge("summarize", "reduce")
    graph.add_edge("reduce", END)

    return graph.compile()


def demo_map_reduce():
    """Demo map-reduce pattern."""

    agent = create_map_reduce_summarizer()

    with open("map_reduce_graph.png", "wb") as f:
        f.write(agent.get_graph().draw_mermaid_png())
    print("\nGraph saved to map_reduce_graph.png")

    documents = [
        "Python is a high-level programming language known for its simplicity and readability. It supports multiple programming paradigms and has a vast ecosystem of libraries.",
        "Machine learning is a subset of AI that enables systems to learn from data. Common approaches include supervised, unsupervised, and reinforcement learning.",
        "Cloud computing provides on-demand access to computing resources. Major providers include AWS, Azure, and Google Cloud Platform.",
    ]

    print("\nMap-Reduce Summarization Demo:\n")

    # All 3 "start" lines print before any "done" line: the branches run in parallel.
    # The "done" order changes from run to run, but `summaries` still comes back in
    # document order: LangGraph merges results in the order the Sends were created.
    result = agent.invoke(
        {"documents": documents, "summaries": [], "final_summary": ""}
    )

    print("\nIndividual summaries:")
    for i, summary in enumerate(result["summaries"]):
        print(f"  {i+1}. {summary}")

    print(f"\nCombined summary:\n{result['final_summary']}")


if __name__ == "__main__":
    demo_map_reduce()
