"""
Agent Communication Patterns in LangGraph - Shared State (Typed Fields)
Agents communicate through structured state fields
"""

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing_extensions import TypedDict
import json
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# Shared state fields: agents fill in a form, each one completing its own section.
#   - SEVERAL named, typed keys, and each agent owns its own
#   - What's passed is structured data (parsed JSON, a real float), not prose
#   - Each agent reads only the fields it needs (the advisor never sees raw_data)
#   - The contract between agents is explicit: it's the state schema, and plain
#     Python can act on it, e.g. route on state["confidence_score"] < 0.5
# Compare with 9_message_passing.py, where agents share one chat transcript.


class SharedFieldsState(TypedDict):
    query: str
    # Each agent writes to its own field — others can read it.
    # Only one node writes each field, so no reducer is needed.
    raw_data: list[dict]  # written by data_collector
    analysis: str  # written by analyst
    recommendations: list[str]  # written by advisor
    confidence_score: float  # written by analyst


def create_shared_fields_pipeline():
    """Agents communicate through typed state fields, not messages."""

    def data_collector(state: SharedFieldsState) -> dict:
        """Collects data and writes to the raw_data field."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a data collector. Given the query, produce 3 data points "
                        "as a JSON array of objects with 'source' and 'finding' keys. "
                        "Return ONLY the JSON array, no markdown."
                    )
                ),
                HumanMessage(content=state["query"]),
            ]
        )

        try:
            data = json.loads(response.text)
        except json.JSONDecodeError:
            data = [{"source": "llm", "finding": response.text}]

        return {"raw_data": data}

    def analyst(state: SharedFieldsState) -> dict:
        """Reads raw_data field, writes analysis and confidence."""
        data_summary = json.dumps(state["raw_data"], indent=2)

        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a data analyst. Analyze the collected data and provide: "
                        "1) A brief analysis (2-3 sentences), and "
                        "2) A confidence score from 0.0 to 1.0. "
                        "Format: ANALYSIS: <text>\nCONFIDENCE: <number>"
                    )
                ),
                HumanMessage(
                    content=f"Query: {state['query']}\n\nData:\n{data_summary}"
                ),
            ]
        )

        content = response.text
        analysis = content
        confidence = 0.7  # default

        if "CONFIDENCE:" in content:
            parts = content.split("CONFIDENCE:")
            analysis = parts[0].replace("ANALYSIS:", "").strip()
            try:
                confidence = float(parts[1].strip())
            except ValueError:
                confidence = 0.7

        return {"analysis": analysis, "confidence_score": confidence}

    def advisor(state: SharedFieldsState) -> dict:
        """Reads analysis + confidence, writes recommendations."""
        response = llm.invoke(
            [
                SystemMessage(
                    content=(
                        "You are a strategic advisor. Based on the analysis and "
                        "confidence score, provide 3 actionable recommendations. "
                        "Return them as a JSON array of strings. "
                        "Return ONLY the JSON array, no markdown."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Query: {state['query']}\n"
                        f"Analysis: {state['analysis']}\n"
                        f"Confidence: {state['confidence_score']}"
                    )
                ),
            ]
        )

        try:
            recs = json.loads(response.text)
        except json.JSONDecodeError:
            recs = [response.text]

        return {"recommendations": recs}

    graph = StateGraph(SharedFieldsState)

    graph.add_node("data_collector", data_collector)
    graph.add_node("analyst", analyst)
    graph.add_node("advisor", advisor)

    graph.add_edge(START, "data_collector")
    graph.add_edge("data_collector", "analyst")
    graph.add_edge("analyst", "advisor")
    graph.add_edge("advisor", END)

    return graph.compile()


def demo_shared_state():
    """Demo shared state fields between agents."""
    agent = create_shared_fields_pipeline()

    print("Shared State Demo:\n")

    result = agent.invoke(
        {
            "query": "Should a small business invest in AI automation in 2026?",
            "raw_data": [],
            "analysis": "",
            "recommendations": [],
            "confidence_score": 0.0,
        }
    )

    print(f"Data collected: {len(result['raw_data'])} points")
    for d in result["raw_data"]:
        print(f"  - [{d.get('source', 'N/A')}] {d.get('finding', 'N/A')[:80]}...")

    print(f"\nAnalysis: {result['analysis'][:200]}...")
    print(f"Confidence: {result['confidence_score']}")

    print(f"\nRecommendations:")
    for i, rec in enumerate(result["recommendations"], 1):
        print(f"  {i}. {rec}")


if __name__ == "__main__":
    demo_shared_state()
