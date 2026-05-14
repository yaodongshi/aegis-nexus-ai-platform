#!/usr/bin/env python3
"""
Minimal fake OpenAI-compatible server for M1.2 CLI testing.
Returns fixed responses so CLI tools can verify gateway authentication and routing.
Usage: python3 scripts/fake_openai_server.py [--port 11434]
"""
import json
import time
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer


FAKE_RESPONSE = {
    "id": "chatcmpl-fake-m12-test",
    "object": "chat.completion",
    "created": int(time.time()),
    "model": "gpt-probe",
    "choices": [
        {
            "index": 0,
            "message": {"role": "assistant", "content": "OK — gateway M1.2 probe successful"},
            "finish_reason": "stop",
        }
    ],
    "usage": {"prompt_tokens": 5, "completion_tokens": 8, "total_tokens": 13},
}

FAKE_MODELS = {
    "object": "list",
    "data": [{"id": "gpt-probe", "object": "model", "created": 0, "owned_by": "fake"}],
}


class FakeHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # suppress default logging

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        try:
            req = json.loads(body)
        except Exception:
            req = {}
        print(f"[fake-openai] POST {self.path} model={req.get('model','?')}")

        resp = FAKE_RESPONSE.copy()
        resp["created"] = int(time.time())
        resp["model"] = req.get("model", "gpt-probe")
        self._json(resp)

    def do_GET(self):
        if "/models" in self.path:
            self._json(FAKE_MODELS)
        else:
            self._json({"status": "ok"})

    def _json(self, data):
        body = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=11434)
    args = parser.parse_args()
    server = HTTPServer(("0.0.0.0", args.port), FakeHandler)
    print(f"[fake-openai] Listening on port {args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
