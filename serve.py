"""The agent behind an OpenAI-compatible chat API, for chat UIs such as Open WebUI.

    python serve.py --repo ../my-project [--port 8000] [--test "python -m pytest -q"] [--key SECRET]

Each request carries the whole conversation and the repository holds the work, so no session store is needed.
The agent edits the repository in place (review or undo with git); its commands still run in the sandbox.
"""

import argparse
import functools
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import agent
import sandbox
from tools import bash

REPO, TEST, KEY = Path("."), "", ""                                     # set from the command line


def traced(tool, send):
    """The same tool, also reporting each call and the first line of its result to the chat."""
    @functools.wraps(tool)
    def run(workdir: Path, **args) -> str:
        result = tool(workdir, **args)
        first = (result.splitlines() or [""])[0][:80]
        send(f"- `{tool.__name__}` {' '.join(map(str, args.values()))[:80]} → {first}\n")
        return result
    return run


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):                                                    # /v1/models: the agent is one model
        self.answer({"object": "list", "data": [{"id": "coding-agent", "object": "model", "owned_by": "local"}]})

    def do_POST(self):                                                   # /v1/chat/completions
        if KEY and self.headers.get("Authorization") != f"Bearer {KEY}":
            return self.answer({"error": {"message": "wrong API key"}}, 401)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        chat = [{"role": m["role"], "content": m["content"] if isinstance(m["content"], str)
                 else " ".join(part.get("text", "") for part in m["content"])}          # text parts only
                for m in body["messages"] if m["role"] in ("user", "assistant")]
        stream = body.get("stream", False)
        if stream:                                                       # progress as server-sent events
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
        tools = [traced(t, self.chunk if stream else lambda text: None) for t in agent.FIXER_TOOLS]
        trace = agent.loop(agent.PROMPTS["coder"], chat[-1]["content"], REPO, tools, seed=len(chat), first=1,
                           history=chat[:-1])
        reply = trace[-1]["reply"] if trace[-1]["action"] == "done" else f"Stopped after step {trace[-1]['step']}."
        reply += f"\n\nTests: {'pass' if bash(REPO, TEST).startswith('exit code 0') else 'fail'}" if TEST else ""
        if not stream:
            message = {"role": "assistant", "content": reply}
            return self.answer({"object": "chat.completion", "model": "coding-agent",
                                "choices": [{"index": 0, "message": message, "finish_reason": "stop"}]})
        self.chunk("\n" + reply)
        self.wfile.write(b"data: [DONE]\n\n")

    def answer(self, data: dict, code: int = 200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def chunk(self, text: str):                                          # one server-sent event, sent at once
        delta = {"object": "chat.completion.chunk", "model": "coding-agent",
                 "choices": [{"index": 0, "delta": {"content": text}}]}
        self.wfile.write(f"data: {json.dumps(delta)}\n\n".encode())
        self.wfile.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="the repository the agent works in")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1", help="0.0.0.0 makes it reachable from other machines")
    parser.add_argument("--test", default="", help="run after every answer, and report pass or fail")
    parser.add_argument("--key", default="", help="require this API key")
    args = parser.parse_args()
    REPO, TEST, KEY = Path(args.repo).resolve(), args.test, args.key
    sandbox.READ_ONLY.clear()                                            # your repository: the tests are yours too
    print(f"coding-agent on http://{args.host}:{args.port}/v1, working in {REPO}, model {agent.MODEL}")
    HTTPServer((args.host, args.port), Handler).serve_forever()
