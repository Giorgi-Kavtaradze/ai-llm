"""
LangGraph Conditional Edges - Conditional Loop
Loop back to an earlier node until a quality check passes
"""

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model("gpt-4o-mini", temperature=0.0)


class QualityState(TypedDict):
    content: str
    quality_score: int
    feedback: str
    final_content: str
    iteration: int


def demo_conditional_loop():

    def evaluate_quality(state: QualityState) -> dict:
        response = llm.invoke(
            f"Rate this content quality from 1-10. Reply with just the number.\n\n"
            f"Content: {state['content']}"
        )
        try:
            score = int(response.content.strip())  # type: ignore
        except:
            score = 5
        return {"quality_score": score}

    def improve_content(state: QualityState) -> dict:
        response = llm.invoke(
            f"Improve this content to be more engaging and clear:\n\n{state['content']}"
        )
        return {"content": response.content, "iteration": state["iteration"] + 1}

    def finalize_content(state: QualityState) -> dict:
        return {
            "final_content": state["content"],
            "feedback": f"Approved after {state['iteration']} iterations with score {state['quality_score']}",
        }

    def should_continue(state: QualityState) -> Literal["improve", "finalize"]:
        if state["quality_score"] >= 7:
            return "finalize"
        elif state["iteration"] >= 3:
            return "finalize"  # Max iterations
        else:
            return "improve"

    graph = StateGraph(QualityState)

    graph.add_node("evaluate", evaluate_quality)
    graph.add_node("improve", improve_content)
    graph.add_node("finalize", finalize_content)

    graph.add_edge(START, "evaluate")

    graph.add_conditional_edges(
        "evaluate", should_continue, {"improve": "improve", "finalize": "finalize"}
    )

    graph.add_edge("improve", "evaluate")  # Loop back!
    graph.add_edge("finalize", END)

    app = graph.compile()

    # visualize the graph
    print("\n--- Mermaid Graph ---")
    print(app.get_graph().draw_mermaid())

    # save as PNG
    png_bytes = app.get_graph().draw_mermaid_png()
    with open("graph_newest.png", "wb") as f:
        f.write(png_bytes)
    print("\nGraph saved to graph_newest.png")

    # Example usage
    print("\nConditional Loop Demo:\n")

    result = app.invoke(
        {
            "content": "AI is cool",
            "quality_score": 0,
            "feedback": "",
            "final_content": "",
            "iteration": 0,
        }
    )

    print(f"Original: AI is cool")
    print(f"Final: {result['final_content'][:200]}...")
    print(f"Feedback: {result['feedback']}")


if __name__ == "__main__":
    demo_conditional_loop()
