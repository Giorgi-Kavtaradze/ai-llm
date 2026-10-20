#!/bin/bash
# PreToolUse hook: Claude Code runs this before every Bash command.
# Claude Code sends the tool call as JSON on stdin.
cmd=$(jq -r '.tool_input.command')

if echo "$cmd" | grep -qE 'rm -rf|git push (-f|--force)'; then
  echo "Blocked by hook: '$cmd' is not allowed in this project." >&2
  exit 2
fi
exit 0
