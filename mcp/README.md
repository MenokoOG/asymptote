# Asymptote as an MCP server: local & cloud

Run Asymptote as a **Model Context Protocol** tool so any AI stack can call it.
It works **both ways**, with frontier APIs (Claude, GPT) *and* with fully
local / self-hosted models (Ollama, LM Studio, vLLM). Pick either; the tool
contract is identical. This guide covers a local (stdio) server for a
workstation and a cloud (HTTP) server for a shared endpoint.

MCP is model-agnostic. If your runtime speaks MCP (or you bridge to it), your
model gets one new tool: `analyze_complexity(code | path)`.

**Two ways to consume it:**
- **A: Frontier / hosted** (Claude Desktop, or an Anthropic/OpenAI
  function-calling loop): easiest, no infra.
- **B: Local / self-hosted** (Ollama, LM Studio, vLLM + an MCP-aware client):
  fully offline, nothing leaves your box.

---

## 0. Install

```bash
cd mcp
python -m venv .venv && . .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt                    # installs `mcp`
```

Smoke-test the engine underneath (no MCP needed):

```bash
cd ..
python agent_tool.py examples/sample.py
```

---

## 1. Local MCP server (stdio)

`stdio` is the default. The **client launches the server** as a subprocess and
talks over stdin/stdout, nothing binds to a port, nothing leaves the machine.

Start it manually to confirm it boots:

```bash
ASYMPTOTE_TRANSPORT=stdio python mcp/server.py
```

Then register it with any MCP client. The config shape is the same everywhere
(Claude Desktop, Cline, Continue, Zed, LibreChat): a command + args.

```jsonc
// mcpServers config (works in most MCP clients)
{
  "mcpServers": {
    "asymptote": {
      "command": "python",
      "args": ["/absolute/path/to/asymptote/mcp/server.py"],
      "env": { "ASYMPTOTE_TRANSPORT": "stdio" }
    }
  }
}
```

---

## 2. Wire it to a model

### Option A: Frontier / hosted models
Zero extra infra. Two common paths:

- **Claude Desktop (or any MCP desktop client):** drop the stdio `mcpServers`
  block from step 1 into the client's config. The frontier model now calls
  `analyze_complexity` and the client runs this server locally for it.
- **Anthropic / OpenAI function-calling loop:** you don't even need MCP,
  advertise `ASYMPTOTE_TOOL` (from `agent_tool.py`) in the request's `tools`
  array, and when the hosted model emits the call, run `run_tool(**args)` and
  return the result. Same dispatcher the MCP server uses.

### Option B: Local / self-hosted models (fully offline)
Keep the model on your own hardware, add Asymptote as a tool.

#### Ollama / LM Studio / vLLM via an MCP-aware client
Point an MCP-capable chat client (LibreChat, Open WebUI + an MCP bridge,
Cline, or a custom loop) at your local model endpoint, then add the stdio
server from step 1. The model calls `analyze_complexity`; the client executes
this process and returns the JSON result. Your code never leaves your box.

#### Minimal DIY loop (any OpenAI-compatible local server)
If your runtime does function-calling but not MCP, skip MCP entirely and call
the engine directly, it is a plain Python function:

```python
from agent_tool import ASYMPTOTE_TOOL, run_tool   # repo root on sys.path

# 1. advertise ASYMPTOTE_TOOL to your local model (Ollama /api/chat "tools",
#    or an OpenAI-compatible /v1/chat/completions "tools" array)
# 2. when the model emits a tool call named "analyze_complexity":
result = run_tool(**tool_call_arguments)
# 3. feed `result` back as the tool message. Done.
```

No network, no keys, no vendor. The tool schema and dispatcher are identical
to what the MCP server wraps.

---

## 3. Cloud / self-hosted server (HTTP)

For a shared team endpoint or a model running on your own server, switch the
transport to HTTP so the server is long-lived and reachable over the network.

### Run directly

```bash
ASYMPTOTE_TRANSPORT=streamable-http python mcp/server.py
# serves MCP over HTTP on 0.0.0.0:8000 (FastMCP default)
```

### Run with Docker (recommended for cloud)

```bash
docker build -t asymptote-mcp -f mcp/Dockerfile .
docker run -d --name asymptote-mcp \
  -e ASYMPTOTE_TRANSPORT=streamable-http \
  -p 8000:8000 asymptote-mcp
```

Deploy that image anywhere that runs a container, your own VPS/homelab, Fly.io,
Render, Railway, or a k8s cluster. Point your MCP client's remote-server URL at
`http(s)://<host>:8000`.

### Client config for a remote server

```jsonc
{
  "mcpServers": {
    "asymptote": { "url": "https://mcp.your-domain.com" }
  }
}
```

### Hardening checklist (do before exposing publicly)
- Terminate TLS at a reverse proxy (Caddy / nginx / Traefik).
- Put an auth layer in front (proxy basic-auth, mTLS, or an API gateway),
  MCP itself does not authenticate callers.
- `path=` reads files on the SERVER. Run the container with a read-only mount
  scoped to the code you intend to analyze; never mount secrets.
- Rate-limit and log at the proxy.

---

## Contract summary

| | |
|---|---|
| Tool name | `analyze_complexity` |
| Args | `code` (string) **or** `path` (string), exactly one |
| Returns | `{ ok, summary, results, disclaimer }` |
| Deps | engine: none · server: `mcp` |

*LAHA: Love All Humans Always.*
