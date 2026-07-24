"""Asymptote MCP server.

Wraps the Asymptote engine as a Model Context Protocol tool so ANY
MCP-capable client can call it — Claude Desktop, LibreChat, Open WebUI,
Cline, or your own agent loop. Works with both frontier APIs (Claude, GPT)
and self-hosted models (Ollama / LM Studio / vLLM) — your choice.

Transports:
  - stdio (default) — local, the client spawns this process
  - streamable-http / sse — cloud, run as a long-lived service

Choose with the ASYMPTOTE_TRANSPORT env var. See ./README.md.
"""
from __future__ import annotations

import os
import sys

# Make the engine importable whether run from here or installed elsewhere.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent_tool import run_tool  # noqa: E402
from mcp.server.fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("asymptote")


@mcp.tool()
def analyze_complexity(code: str | None = None, path: str | None = None) -> dict:
    """Estimate time & space Big-O complexity of Python code.

    Provide exactly one of:
      code: raw Python source to analyze
      path: absolute path to a .py file or directory on the server

    Returns per-function estimates with confidence scores and explicit
    unknowns. This is a static heuristic, not a proof.
    """
    return run_tool(code=code, path=path)


def main() -> None:
    transport = os.environ.get("ASYMPTOTE_TRANSPORT", "stdio")
    # stdio for local clients; streamable-http / sse for cloud deployment.
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
