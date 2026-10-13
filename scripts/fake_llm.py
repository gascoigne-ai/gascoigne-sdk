#!/usr/bin/env python3
"""A stand-in for the LLM API, so the proxy demos run without an API key.

It speaks the OpenAI chat-completions protocol: the first request gets a call to `search_logs`,
the request that carries the tool result gets a final answer. Usage:

    scripts/fake_llm.py 8099 &
    printf 'receivers:\n  httpproxy:\n    openai: http://127.0.0.1:8099\n' > /tmp/fake.yaml
    GASCOIGNE_CONFIG=/tmp/fake.yaml OPENROUTER_API_KEY=fake uv run python langgraph/proxy.py
"""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

ANSWER = "The database connection pool was exhausted and timed out after 30 seconds."
TOOL_CALL = {
    "id": "call_1",
    "type": "function",
    "function": {"name": "search_logs", "arguments": "{}"},
}


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        body = json.loads(self.read_body())
        has_result = any(m.get("role") == "tool" for m in body.get("messages", []))
        message = {"role": "assistant", "content": ANSWER if has_result else None}
        if not has_result:
            message["tool_calls"] = [TOOL_CALL]
        finish = "stop" if has_result else "tool_calls"
        model = body.get("model", "fake")
        if body.get("stream"):
            self.stream(model, message, finish)
        else:
            self.send_json(model, message, finish)

    def read_body(self) -> bytes:
        """The request body, whether it came with a length or chunked."""
        if "Content-Length" in self.headers:
            return self.rfile.read(int(self.headers["Content-Length"]))
        body = b""
        while size := int(self.rfile.readline().strip() or b"0", 16):
            body += self.rfile.read(size)
            self.rfile.readline()
        return body

    def send_json(self, model: str, message: dict, finish: str) -> None:
        reply = json.dumps(
            {
                "id": "fake",
                "object": "chat.completion",
                "created": 0,
                "model": model,
                "choices": [{"index": 0, "message": message, "finish_reason": finish}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(reply)))
        self.end_headers()
        self.wfile.write(reply)

    def stream(self, model: str, message: dict, finish: str) -> None:
        """The same answer as server-sent events, as streaming clients expect."""
        delta = {"role": "assistant", "content": message["content"]}
        if "tool_calls" in message:
            delta["tool_calls"] = [{"index": 0, **TOOL_CALL}]
        chunks = [
            {"choices": [{"index": 0, "delta": delta, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]},
        ]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()
        for chunk in chunks:
            chunk.update(id="fake", object="chat.completion.chunk", created=0, model=model)
            self.wfile.write(f"data: {json.dumps(chunk)}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")

    def log_message(self, *_: object) -> None:
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", int(sys.argv[1])), Handler).serve_forever()
