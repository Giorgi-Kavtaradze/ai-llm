---
name: explain-code
description: Explain a Python file from this course to a beginner, step by step. Use when the user asks what a file does or how it works.
argument-hint: <file>
allowed-tools: Read
---

Explain the file $ARGUMENTS to someone who is new to Python and LLMs.

1. Start with one sentence: what does this script do, and what will the user see when they run it?
2. List what it needs before it runs: packages, API keys from `.env`, local services such as Ollama.
3. Walk through the code top to bottom in small chunks. For each chunk, quote the few key lines and explain why they are there, not just what they do.
4. Name the one or two ideas from the course this file is meant to teach (for example: tool calling, state reducers, supervisor pattern).
5. End with one small change the user could try to learn more, and what they should expect to happen.

Keep it short and plain. Do not explain basic Python syntax unless it is unusual.
