# Asymptote

**Static time & space complexity (Big-O) estimator for Python, built for agents.**

> *For people who enjoy algorithms.* Asymptote is named for the curve that
> complexity is really about, the line your runtime approaches as `n` grows.

Point it at a `.py` file or a directory and it reports, per function, the
estimated **time** and **space** Big-O, a **confidence** score, the
**evidence** behind the call, and, crucially, the **unknowns** it could not
determine. Use it from the CLI, as an agent tool, or as an MCP server.

---

## Why "unknowns" instead of false certainty

The exact complexity of an arbitrary program is **undecidable**, it reduces
to the halting problem. Asymptote is a *heuristic*, and it says so. Rather than
bluff, it lowers its confidence and names its blind spots (recursion depth,
cross-function calls) so you can judge the estimate instead of trusting a
label. Unknown data should increase your discipline, not the tool's confidence.

## Install

Zero runtime dependencies: Python 3.10+ standard library only.

```bash
git clone https://github.com/<you>/asymptote
cd asymptote
```

## CLI usage

```bash
python asymptote.py examples/sample.py          # human-readable report
python asymptote.py examples/sample.py --json    # machine-readable JSON
python asymptote.py .                             # analyze a whole tree
```

## Agent-tool usage

`agent_tool.py` exposes a JSON-Schema tool definition (`ASYMPTOTE_TOOL`) and a
`run_tool()` dispatcher. Register the schema with any function-calling model
and route the call to `run_tool`:

```python
from agent_tool import ASYMPTOTE_TOOL, run_tool

result = run_tool(code="def f(xs):\n    return sorted(xs)")
# {"ok": True, "summary": {...}, "results": {...}}
```

## MCP server (local & cloud, frontier & self-hosted)

Run Asymptote as a Model Context Protocol tool so your model, frontier
(Claude, GPT) or fully local (Ollama, LM Studio, vLLM), gets one new tool:
`analyze_complexity(code | path)`. See [`mcp/README.md`](mcp/README.md) for
stdio (local) and HTTP/Docker (cloud) setup.

## How it works (the cost algebra)

Asymptote walks the AST and composes a small `Cost` term
`(degree, logs, exp, fact)` over the input size `n`:

- **Sequential** statements → dominant term wins
- **Nested** loops → terms multiply, raising the polynomial degree
- **`sorted()` / `.sort()`** → contributes an `n log n` term
- **`while` with `// 2`** → recognized as divide-and-conquer → `log n`
- **Recursion**, 1 self-call → `O(n)` (or `O(log n)` if halving);
  2+ self-calls → `O(2^n)` (or `O(n log n)` if halving)

## Known limits (stated, not hidden)

- Python only (v0.1). The AST approach ports to other languages via a
  language-specific front end feeding the same `Cost` algebra.
- Cross-function costs are **not** inlined, they are listed as unknowns.
- Loop bounds are assumed to scale with `n`; a loop over a true constant is
  over-counted. Confidence and evidence flag the ambiguous cases.
- Memoized recursion is reported at its un-memoized upper bound.

Asymptote is a **decision aid**, not an oracle. Read the evidence, not just
the label.

## Development

```bash
pip install -r requirements-dev.txt
python -m pyflakes asymptote.py agent_tool.py mcp tests examples
python -m pytest
```

## License

MIT, see [`LICENSE`](LICENSE).

---

The design philosophy is that *unknown data must increase decision discipline, not
model confidence*. Driven by **LAHA: Love All Humans Always.**
