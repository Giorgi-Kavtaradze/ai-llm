"""
LangGraph Core Concepts - Multi-Node Graph
Chaining several LLM nodes in sequence
"""

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()


# === Multi-Node Graph ===
class MultiStepState(TypedDict):
    input: str
    analyzed: str
    enhanced: str
    final: str


def demo_multi_node_graph():
    llm = init_chat_model("gpt-4o-mini", temperature=0)

    def analyze_node(state: MultiStepState) -> dict:
        response = llm.invoke(
            [
                HumanMessage(
                    content=f"Analyze the following input and summarize it in one sentence: {state['input']}"
                )
            ]
        )
        return {"analyzed": response.content}

    def enhance(state: MultiStepState) -> dict:
        response = llm.invoke(
            [
                HumanMessage(
                    content=f"Take the following analysis and enhance it with more details: {state['analyzed']}"
                )
            ]
        )

        return {"enhanced": response.content}

    def finalize(state: MultiStepState) -> dict:
        response = llm.invoke(
            [
                HumanMessage(
                    content=f"Take the following enhanced analysis and finalize it into a concise summary: {state['enhanced']}"
                )
            ]
        )
        return {"final": response.content}

    graph = StateGraph(MultiStepState)
    graph.add_node("analyze_node", analyze_node)
    graph.add_node("enhance_node", enhance)
    graph.add_node("finalize_node", finalize)

    graph.add_edge(START, "analyze_node")
    graph.add_edge("analyze_node", "enhance_node")
    graph.add_edge("enhance_node", "finalize_node")
    graph.add_edge("finalize_node", END)

    app = graph.compile()

    # # visualize the graph
    print("\n--- Mermaid Graph ---")
    print(app.get_graph().draw_mermaid())

    # save as PNG
    png_bytes = app.get_graph().draw_mermaid_png()
    with open("graph_3.png", "wb") as f:
        f.write(png_bytes)

    result = app.invoke({"input": "Artificial intelligence"}) # type: ignore

    print("\nMulti-Node Graph Result:")
    print(f"  Input: {result['input']}")
    print(f"  Analyzed: {result['analyzed'][:100]}...")
    print(f"  Enhanced: {result['enhanced'][:100]}...")
    print(f"  Final: {result['final']}")


if __name__ == "__main__":
    demo_multi_node_graph()
