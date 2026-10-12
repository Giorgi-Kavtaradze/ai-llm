"""
LangGraph Conditional Edges - Multi-Path Routing
Route on several analysed attributes at once
"""

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model("gpt-4o-mini", temperature=0.0)


def demo_multi_path_routing():
    class TaskState(TypedDict):
        task: str
        urgency: str
        complexity: str
        handler: str
        result: str

    def analyze_task(state: TaskState) -> dict:
        # Analyze urgency
        urgency_response = llm.invoke(
            f"Is this task urgent? Reply 'urgent' or 'normal'.\nTask: {state['task']}"
        )

        # Analyze complexity
        complexity_response = llm.invoke(
            f"Is this task complex? Reply 'complex' or 'simple'.\nTask: {state['task']}"
        )

        return {
            "urgency": urgency_response.content.lower().strip(),  # type: ignore
            "complexity": complexity_response.content.lower().strip(),  # type: ignore
        }

    def urgent_complex_handler(state: TaskState) -> dict:
        return {
            "handler": "Senior Team",
            "result": "Escalated to senior team for immediate action",
        }

    def urgent_simple_handler(state: TaskState) -> dict:
        return {
            "handler": "Quick Response",
            "result": "Handled immediately by available agent",
        }

    def normal_complex_handler(state: TaskState) -> dict:
        return {
            "handler": "Specialist",
            "result": "Assigned to specialist for thorough handling",
        }

    def normal_simple_handler(state: TaskState) -> dict:
        return {
            "handler": "Standard",
            "result": "Added to standard queue",
        }

    def route_task(state: TaskState) -> str:
        is_urgent = "urgent" in state["urgency"]
        is_complex = "complex" in state["complexity"]

        if is_urgent and is_complex:
            return "urgent_complex"
        elif is_urgent:
            return "urgent_simple"
        elif is_complex:
            return "normal_complex"
        else:
            return "normal_simple"

    graph = StateGraph(TaskState)

    graph.add_node("analyze", analyze_task)
    graph.add_node("urgent_complex", urgent_complex_handler)
    graph.add_node("urgent_simple", urgent_simple_handler)
    graph.add_node("normal_complex", normal_complex_handler)
    graph.add_node("normal_simple", normal_simple_handler)

    graph.add_edge(START, "analyze")
    graph.add_conditional_edges(
        "analyze",
        route_task,
        {
            "urgent_complex": "urgent_complex",
            "urgent_simple": "urgent_simple",
            "normal_complex": "normal_complex",
            "normal_simple": "normal_simple",
        },
    )

    for node in ["urgent_complex", "urgent_simple", "normal_complex", "normal_simple"]:
        graph.add_edge(node, END)

    app = graph.compile()

    # visualize the graph
    print("\n--- Mermaid Graph ---")
    print(app.get_graph().draw_mermaid())

    # save as PNG
    png_bytes = app.get_graph().draw_mermaid_png()
    with open("graph_complex.png", "wb") as f:
        f.write(png_bytes)
    print("\nGraph saved to graph_complex.png")

    print("\nMulti-Path Routing Demo:\n")

    tasks = [
        "Server is down! Need immediate fix!",
        "Update the documentation for the API",
        "Redesign the entire database schema",
        "Fix the typo on the homepage",
    ]

    for task in tasks:
        result = app.invoke({"task": task})  # type: ignore
        print(f"Task: {task}")
        print(f"Urgency: {result['urgency']} | Complexity: {result['complexity']}")
        print(f"Handler: {result['handler']}")
        print(f"Result: {result['result']}")
        print("-" * 40)


if __name__ == "__main__":
    demo_multi_path_routing()
