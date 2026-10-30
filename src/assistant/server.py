"""A small HTTP server for the chat page, built on the standard library.

Routes:
  GET  /             the chat page (ui/index.html)
  GET  /api/health   status and the configured AI provider
  POST /api/chat     {"message": str, "session_id": str | null} -> response from process_request
  POST /api/reset    {"session_id": str}
"""
from __future__ import annotations

import argparse
import json
import sys
import threading
import traceback
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from assistant import UI_DIR, llm
from assistant.service import Session, process_request

MAX_BODY_BYTES = 16_000
SESSIONS: dict[str, Session] = {}
LOCK = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    provider = None

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict | None:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        try:
            data = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return data if isinstance(data, dict) else None

    def do_GET(self) -> None:  # noqa: N802 - http.server naming
        if self.path in ("/", "/index.html"):
            page = UI_DIR / "index.html"
            self._send(200, page.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/health":
            self._json(200, {"status": "ok", "ai_provider": self.provider.name if self.provider else None})
        else:
            self._json(404, {"error": "Not found."})

    def do_POST(self) -> None:  # noqa: N802
        data = self._read_json()
        if data is None:
            self._json(400, {"error": "Send a JSON object no larger than 16 KB."})
            return
        if self.path == "/api/reset":
            with LOCK:
                SESSIONS.pop(str(data.get("session_id")), None)
            self._json(200, {"status": "cleared"})
            return
        if self.path != "/api/chat":
            self._json(404, {"error": "Not found."})
            return
        session_id = data.get("session_id") if isinstance(data.get("session_id"), str) else None
        with LOCK:
            if session_id not in SESSIONS:
                session_id = uuid.uuid4().hex
                SESSIONS[session_id] = Session()
            session = SESSIONS[session_id]
            try:
                result = process_request(data.get("message"), session, provider=self.provider)
            except ValueError as exc:
                self._json(400, {"error": str(exc), "session_id": session_id})
                return
            except Exception:  # noqa: BLE001 - never leak internals to the page
                traceback.print_exc()
                self._json(500, {"error": "Something went wrong while handling that message. Try again.", "session_id": session_id})
                return
        self._json(200, {"session_id": session_id, **result})


def make_server(host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    try:
        Handler.provider = llm.get_provider()
    except llm.LLMError as exc:
        print(f"AI provider disabled: {exc}", file=sys.stderr)
        Handler.provider = None
    return ThreadingHTTPServer((host, port), Handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m assistant serve", description="Run the chat page.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    server = make_server(args.host, args.port)
    ai = Handler.provider.name if Handler.provider else "off (rule-based only)"
    print(f"Student Learning Assistant running at http://{args.host}:{args.port}  (AI provider: {ai})")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
