# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-07-24
### Added
- **Asymptote** engine (`asymptote.py`): static AST-based time & space Big-O
  estimator with a `Cost` algebra, per-function confidence scores, and
  explicit unknowns. CLI (`--json` mode) included.
- Agent-tool wrapper (`agent_tool.py`): JSON-Schema tool definition
  (`ASYMPTOTE_TOOL`) + `run_tool()` dispatcher for function-calling models.
- MCP server (`mcp/`): FastMCP wrapper exposing `analyze_complexity` over
  stdio (local) and streamable-http (cloud). Works with both frontier APIs
  and self-hosted / open models. Dockerfile + deployment guide included.
- Test suite (`tests/`) + GitHub Actions CI (pyflakes + pytest, py3.10/3.12).
- Reference examples with known complexities (`examples/sample.py`).

[0.1.0]: https://example.com/asymptote/releases/tag/v0.1.0
