"""HTTP-level fake AI provider. Speaks the OpenAI-compatible and Anthropic
message APIs and records every request it receives, so tests can assert on
exactly what left the machine."""
from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass
class RecordedRequest:
    path: str
    headers: dict[str, str]
    body: dict
    raw: str


@dataclass
class FakeProvider:
    reply: str = "fake reply"
    status: int = 200
    requests: list[RecordedRequest] = field(default_factory=list)
    _server: ThreadingHTTPServer | None = None
    _thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        assert self._server is not None, "provider not started"
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def start(self) -> "FakeProvider":
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # silence
                pass

            def do_POST(self):
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length).decode("utf-8")
                try:
                    body = json.loads(raw) if raw else {}
                except json.JSONDecodeError:
                    body = {}
                owner.requests.append(
                    RecordedRequest(
                        path=self.path,
                        headers={k.lower(): v for k, v in self.headers.items()},
                        body=body,
                        raw=raw,
                    )
                )
                if owner.status != 200:
                    payload = {"error": {"message": "fake provider error"}}
                    code = owner.status
                elif self.path.endswith("/messages"):
                    payload = {"content": [{"type": "text", "text": owner.reply}]}
                    code = 200
                else:
                    payload = {"choices": [{"message": {"role": "assistant", "content": owner.reply}}]}
                    code = 200
                data = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def all_text(self) -> str:
        """Everything the provider ever received, headers included."""
        return "\n".join(
            r.raw + json.dumps(r.headers) for r in self.requests
        )
