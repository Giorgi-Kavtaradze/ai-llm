"""Call Claude Code from Python with `claude -p`.

Usage (from the repo root):
    python "13. claude-code/examples/scripts/ask_claude.py" "10. LangGraph"

Needs Claude Code installed and logged in. Each run uses your Claude account.
"""

import json
import subprocess
import sys


def ask_claude(prompt, allowed_tools="Read,Glob", model="haiku", max_budget_usd=0.25):
    """Run one Claude Code task without a chat window and return its JSON result."""
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        # In -p mode nobody can approve a prompt, so list the tools it may use.
        "--allowedTools", allowed_tools,
        # A small model is enough for summaries and much cheaper.
        "--model", model,
        # Hard stop in case the task goes off track.
        "--max-budget-usd", str(max_budget_usd),
    ]
    # stdin=DEVNULL: otherwise claude waits a few seconds for piped input.
    completed = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if completed.returncode != 0:
        raise RuntimeError(f"claude failed ({completed.returncode}): {completed.stderr or completed.stdout}")
    return json.loads(completed.stdout)


if __name__ == "__main__":
    lesson = sys.argv[1] if len(sys.argv) > 1 else "10. LangGraph"

    answer = ask_claude(
        f'List the Python files in the folder "{lesson}" and describe each one in one line. '
        "Read only the first 30 lines of each file. Answer as a Markdown list."
    )

    print(answer["result"])
    print()
    print(f"turns: {answer['num_turns']}  cost: ${answer['total_cost_usd']:.4f}  session: {answer['session_id']}")
