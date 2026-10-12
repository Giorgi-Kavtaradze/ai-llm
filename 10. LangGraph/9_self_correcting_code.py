"""
Cycles and Loops in LangGraph - Self-Correcting Code
Generate code, validate it, and loop back to fix errors
"""

from langchain.chat_models import init_chat_model
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict, Annotated
from typing import Literal
import operator
from dotenv import load_dotenv

load_dotenv()

llm = init_chat_model("gpt-4o-mini", temperature=0.0)


class CodeGenState(TypedDict):
    task: str
    code: str
    errors: Annotated[list[str], operator.add]
    iteration: int
    max_iterations: int
    success: bool


def demo_self_correcting_code():
    """Self-correcting code generator."""

    def generate_code(state: CodeGenState) -> dict:
        if state["iteration"] == 0:
            # First attempt
            prompt = f"Write Python code for: {state['task']}\nReturn only the code."
        else:
            # Correction attempt
            prompt = (
                f"Task: {state['task']}\n\n"
                f"Fix this Python code:\n{state['code']}\n\n"
                f"Errors:\n{state['errors'][-1]}\n\n"
                "Return only the corrected code."
            )

        response = llm.invoke(prompt)
        code = response.content.strip() # type: ignore

        # Clean up markdown code blocks if present
        if code.startswith("```"):
            code = code.split("```")[1]
            if code.startswith("python"):
                code = code[6:]

        return {"code": code, "iteration": state["iteration"] + 1}

    def validate_code(state: CodeGenState) -> dict:
        code = state["code"]

        # Step 1: Does it compile?
        try:
            compile(code, "<string>", "exec")
        except SyntaxError as e:
            return {"errors": [f"SyntaxError: {e}"], "success": False}

        # Step 2: Does it RUN and produce correct results?
        test_cases = [
            (0, 1),  # base case
            (1, 1),  # base case
            (5, 120),  # normal case
            (10, 3628800),  # larger input
        ]

        namespace = {}
        try:
            exec(code, namespace)
        except Exception as e:
            return {"errors": [f"Runtime error: {e}"], "success": False}

        if "factorial" not in namespace:
            return {"errors": ["Function 'factorial' not found in code"], "success": False}

        for n, expected in test_cases:
            try:
                result = namespace["factorial"](n)
                if result != expected:
                    return {
                        "errors": [
                            f"factorial({n}) returned {result}, expected {expected}"
                        ],
                        "success": False,
                    }
            except Exception as e:
                return {"errors": [f"factorial({n}) raised {e}"], "success": False}

        return {"success": True}

    def should_continue(state: CodeGenState) -> Literal["generate", "end"]:
        if state["success"]:
            return "end"
        elif state["iteration"] >= state["max_iterations"]:
            return "end"
        else:
            return "generate"

    def finalize(state: CodeGenState) -> dict:
        return state # type: ignore

    graph = StateGraph(CodeGenState)

    graph.add_node("generate", generate_code)
    graph.add_node("validate", validate_code)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "generate")
    graph.add_edge("generate", "validate")
    graph.add_conditional_edges(
        "validate", should_continue, {"generate": "generate", "end": "finalize"}
    )  # Loop back to "generate" if not successful and under max iterations, otherwise go to "finalize"
    graph.add_edge("finalize", END)

    app = graph.compile()

    # visualize the graph
    print("\n--- Mermaid Graph ---")
    # print(app.get_graph().draw_mermaid())

    # save as PNG
    png_bytes = app.get_graph().draw_mermaid_png()
    with open("graph_code.png", "wb") as f:
        f.write(png_bytes)
    print("\nGraph saved to graph_code.png")

    print("Self-Correcting Code Generator:\n")

    result = app.invoke(
        {
            "task": "a function `factorial(n)` that calculates factorial recursively",
            "code": "",
            "errors": [],
            "iteration": 0,
            "max_iterations": 3,
            "success": False,
        }
    )

    print(f"Task: {result['task']}")
    print(f"Iterations: {result['iteration']}")
    print(f"Success: {result['success']}")
    print(f"Final Code:\n{result['code']}")


if __name__ == "__main__":
    demo_self_correcting_code()
