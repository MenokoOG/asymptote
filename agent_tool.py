"""Asymptote agent-tool wrapper.

Exposes the Asymptote engine as a single agent-callable function plus a
JSON-Schema tool definition. Any agent runtime (Claude tool-use, an OpenAI
function-calling loop, a local model via Ollama/LM Studio, or the MCP server
in ./mcp/server.py) can import ASYMPTOTE_TOOL and dispatch to run_tool().

Design note: this file has ONE responsibility, adapt the engine to the
agent tool-call contract. The analysis logic lives in asymptote.py.
"""
from __future__ import annotations

from typing import Any

import asymptote

# JSON-Schema definition an agent registers as a callable tool.
ASYMPTOTE_TOOL: dict[str, Any] = {
    "name": "analyze_complexity",
    "description": (
        "Estimate the time and space complexity (Big-O) of Python source code. "
        "Returns a per-function estimate with a confidence score and an explicit "
        "list of unknowns. Static heuristic, not a proof."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "code": {
                "type": "string",
                "description": "Python source to analyze. Provide this or 'path'.",
            },
            "path": {
                "type": "string",
                "description": "Absolute path to a .py file or directory. Provide this or 'code'.",
            },
        },
        "additionalProperties": False,
    },
}


def run_tool(code: str | None = None, path: str | None = None) -> dict[str, Any]:
    """Dispatch an `analyze_complexity` tool call. Returns a JSON-safe dict.

    Exactly one of `code` or `path` must be supplied.
    """
    if bool(code) == bool(path):
        return {"ok": False, "error": "Provide exactly one of 'code' or 'path'."}

    try:
        if code is not None:
            reports = {"<inline>": asymptote.analyze_source(code)}
        else:
            reports = asymptote.analyze_path(path)  # type: ignore[arg-type]
    except SyntaxError as exc:
        return {"ok": False, "error": f"Syntax error: {exc.msg} (line {exc.lineno})"}
    except (OSError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}

    payload = {p: [r.as_dict() for r in rs] for p, rs in reports.items()}
    functions = [r for rs in payload.values() for r in rs]
    return {
        "ok": True,
        "summary": {
            "functions_analyzed": len(functions),
            "low_confidence": sum(1 for f in functions if f["confidence"] < 0.6),
        },
        "results": payload,
        "disclaimer": "Static heuristic estimate. Unknowns are stated, not hidden.",
    }


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print(json.dumps(ASYMPTOTE_TOOL, indent=2))
    else:
        print(json.dumps(run_tool(path=sys.argv[1]), indent=2))
