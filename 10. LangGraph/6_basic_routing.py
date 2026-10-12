"""
LangGraph Conditional Edges - Basic Routing
Classify a query and route it to a matching handler node
"""

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model("gpt-4o-mini", temperature=0.0)


class RouterState(TypedDict):
    query: str
    query_type: str
    response: str


def demo_basic_routing():
    def classify_query(state: RouterState) -> dict:
        response = llm.invoke(
            f"Classify this query as 'question', 'command', or 'statement'. "
            f"Reply with just the word.\n\n{state['query']}"
        )
        return {"query_type": response.content.lower().strip()}  # type: ignore

    def handle_question(state: RouterState) -> dict:
        response = llm.invoke(f"Answer this question: {state['query']}")
        return {"response": f"[Answer] {response.content}"}

    def handle_command(state: RouterState) -> dict:
        return {"response": f"[Executing] I'll help you with: {state['query']}"}

    def handle_statement(state: RouterState) -> dict:
        return {"response": f"[Acknowledged] Thanks for sharing: {state['query']}"}

    def route_by_type(
        state: RouterState,
    ) -> Literal["question", "command", "statement"]:
        qt = state["query_type"]
        if "question" in qt:
            return "question"
        elif "command" in qt:
            return "command"
        else:
            return "statement"

    graph = StateGraph(RouterState)

    graph.add_node("classify", classify_query)
    graph.add_node("handle_question", handle_question)
    graph.add_node("handle_command", handle_command)
    graph.add_node("handle_statement", handle_statement)

    graph.add_edge(START, "classify")
    graph.add_conditional_edges(
        "classify",  # source node
        route_by_type,  # function that determines which edge to take based on the state
        {
            "question": "handle_question",
            "command": "handle_command",
            "statement": "handle_statement",
        },
    )

    graph.add_edge("handle_question", END)
    graph.add_edge("handle_command", END)
    graph.add_edge("handle_statement", END)

    app = graph.compile()

    # # visualize the graph
    # print("\n--- Mermaid Graph ---")
    # print(app.get_graph().draw_mermaid())

    # # save as PNG
    # png_bytes = app.get_graph().draw_mermaid_png()
    # with open("graph_new.png", "wb") as f:
    #     f.write(png_bytes)
    # print("\nGraph saved to graph_new.png")

    # Example usage
    queries = [
        "What is the capital of France?",
        "Send an email to John",
        "I love programming",
    ]

    for query in queries:
        result = app.invoke({"query": query})  # type: ignore
        print(f"Query: {query}")
        print(f"Type: {result['query_type']}")
        print(f"Response: {result['response']}")
        print("-" * 40)


if __name__ == "__main__":
    demo_basic_routing()
