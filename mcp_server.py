"""The fixer's tools served over MCP (Model Context Protocol; stdio transport: JSON-RPC 2.0, one message per line).

    python mcp_server.py <project folder>

With AGENT_MCP=1 the harness starts one server per attempt and the agent discovers its tools with tools/list, so a
tool can be added here, or served by any other MCP server, without touching agent.py.
"""

import json
import sys
from pathlib import Path

from agent import FIXER_TOOLS
from utils import tool_spec

workdir, tools = Path(sys.argv[1]), {t.__name__: t for t in FIXER_TOOLS}


def call(params: dict) -> dict:
    """tools/call: run one tool. A call that does not fit a tool comes back as an error result, not a crash."""
    try:
        text, error = tools[params["name"]](workdir, **params.get("arguments", {})), False
    except (KeyError, TypeError) as problem:
        text, error = f"Nothing was run: {problem!r}. The tools are: {', '.join(tools)}.", True
    return {"content": [{"type": "text", "text": text}], "isError": error}


METHODS = {
    "initialize": lambda params: {"protocolVersion": params.get("protocolVersion", "2025-06-18"),
                                  "capabilities": {"tools": {}}, "serverInfo": {"name": "agent-tools", "version": "1"}},
    "tools/list": lambda params: {"tools": [{"name": s["name"], "description": s["description"], "inputSchema": s["parameters"]}
                                            for s in (tool_spec(t)["function"] for t in tools.values())]},
    "tools/call": call,
}

for line in sys.stdin:                                    # until the client closes the pipe
    message = json.loads(line)
    if "id" in message:                                   # requests get an answer, notifications do not
        method = message["method"]
        answer = ({"result": METHODS[method](message.get("params", {}))} if method in METHODS
                  else {"error": {"code": -32601, "message": f"unknown method {method}"}})
        print(json.dumps({"jsonrpc": "2.0", "id": message["id"], **answer}), flush=True)
