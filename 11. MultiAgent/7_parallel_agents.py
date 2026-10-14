"""
Parallel Agent Execution in LangGraph
Running multiple agents simultaneously
"""

from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from typing_extensions import TypedDict
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)


# Fan-out / fan-in pattern:
#   START -> [research, creative, technical] run AT THE SAME TIME -> synthesize -> END
# The 3 branches are fixed in the graph. (8_map_reduce.py makes the number of
# branches dynamic, decided at runtime.)


# Each parallel agent writes to its OWN key, so no reducer is needed.
# If two branches wrote the same plain key in the same step, LangGraph would raise
# an error, because it can't know which value to keep.
class ParallelState(TypedDict):
    query: str  # input, read by all three agents
    research_result: str  # written only by research_agent
    creative_result: str  # written only by creative_agent
    technical_result: str  # written only by technical_agent
    final_synthesis: str  # written by synthesize, after all three finish


def create_parallel_research():
    """Three research agents working in parallel."""

    # Three specialists: same query, different system prompt = different perspective
    def research_agent(state: ParallelState) -> dict:
        """Academic/factual research."""
        response = llm.invoke(
            [
                SystemMessage(
                    content="You are an academic researcher. Provide factual, well-sourced information."
                ),
                HumanMessage(content=f"Research this topic: {state['query']}"),
            ]
        )
        return {"research_result": response.content}

    def creative_agent(state: ParallelState) -> dict:
        """Creative perspectives."""
        response = llm.invoke(
            [
                SystemMessage(
                    content="You are a creative thinker. Provide novel perspectives and ideas."
                ),
                HumanMessage(content=f"Give creative insights on: {state['query']}"),
            ]
        )
        return {"creative_result": response.content}

    def technical_agent(state: ParallelState) -> dict:
        """Technical analysis."""
        response = llm.invoke(
            [
                SystemMessage(
                    content="You are a technical analyst. Provide practical, implementation-focused insights."
                ),
                HumanMessage(content=f"Analyze technically: {state['query']}"),
            ]
        )
        return {"technical_result": response.content}

    # Fan-in: runs once, after all three agents are done, so every *_result is filled in
    def synthesize(state: ParallelState) -> dict:
        """Combine all perspectives."""
        synthesis_prompt = f"""Synthesize these three perspectives into a comprehensive response:

        RESEARCH: {state['research_result']}

        CREATIVE: {state['creative_result']}

        TECHNICAL: {state['technical_result']}

        Create a unified, well-structured response."""

        response = llm.invoke(
            [
                SystemMessage(
                    content="You are an expert synthesizer. Combine multiple perspectives into coherent insights."
                ),
                HumanMessage(content=synthesis_prompt),
            ]
        )
        return {"final_synthesis": response.content}

    graph = StateGraph(ParallelState)

    graph.add_node("research", research_agent)
    graph.add_node("creative", creative_agent)
    graph.add_node("technical", technical_agent)
    graph.add_node("synthesize", synthesize)

    # Fan-out: START goes to all three agents
    # Several edges leaving the same node = those nodes run in parallel, in the same step
    graph.add_edge(START, "research")
    graph.add_edge(START, "creative")
    graph.add_edge(START, "technical")

    # Fan-in: several edges INTO one node.
    # Here synthesize runs once, after all three, because the three agents finish
    # in the SAME step (each branch is a single node).
    # If the branches had different lengths, separate edges would trigger synthesize
    # once per branch as each finished. To wait for all of them, use one edge from a
    # list of nodes:  graph.add_edge(["research", "creative", "technical"], "synthesize")
    graph.add_edge("research", "synthesize")
    graph.add_edge("creative", "synthesize")
    graph.add_edge("technical", "synthesize")

    graph.add_edge("synthesize", END)

    return graph.compile()


def demo_parallel_execution():
    """Demo parallel agent execution."""

    agent = create_parallel_research()

    with open("parallel_agent_graph.png", "wb") as f:
        f.write(agent.get_graph().draw_mermaid_png())
    print("\nGraph saved to parallel_agent_graph.png")

    print("Parallel Agent Execution Demo:\n")

    # One invoke() runs the whole fan-out/fan-in. Because the 3 agents run in
    # parallel, total time is about the slowest agent, not the sum of all three.
    result = agent.invoke(
        {
            "query": "The future of remote work",
            "research_result": "",
            "creative_result": "",
            "technical_result": "",
            "final_synthesis": "",
        }
    )

    print("Individual Perspectives:")
    print(f"\n[Research]\n{result['research_result'][:300]}...")
    print(f"\n[Creative]\n{result['creative_result'][:300]}...")
    print(f"\n[Technical]\n{result['technical_result'][:300]}...")

    print(f"\n{'='*50}")
    print(f"[SYNTHESIZED]\n{result['final_synthesis']}")


if __name__ == "__main__":
    demo_parallel_execution()
