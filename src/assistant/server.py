"""A small HTTP server for the chat page, built on the standard library.

Routes:
  GET  /             the chat page (ui/index.html)
  GET  /api/health   status and the configured AI provider
  POST /api/chat     {"message": str, "session_id": str | null} -> response from process_request
  POST /api/reset    {"session_id": str}  deletes everything stored for that session

Sessions are stored in SQLite (data/assistant.db, or ASSISTANT_DB), so a plan survives a
restart. The session id is a random UUID4 that only the browser holding it knows.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import traceback
import uuid
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from assistant import DATA_DIR, UI_DIR, llm, storage
from assistant.service import Session, process_request

MAX_BODY_BYTES = 16_000
# Sent with every response. The page uses inline CSS/JS and Google Fonts, nothing else.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
    ),
}
SESSION_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _session_lock(session_id: str) -> threading.Lock:
    """One lock per session: two tabs of one student wait for each other, other students don't."""
    with _locks_guard:
        return _locks.setdefault(session_id, threading.Lock())


class Handler(BaseHTTPRequestHandler):
    provider = None
    db_path = DATA_DIR / "assistant.db"
    timeout = 15  # seconds a connection may sit idle or half-sent before it is dropped (slowloris)
    server_version = "assistant"  # no Python version in the Server header
    sys_version = ""

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:  # "Content-Length: abc"
            return None
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        try:
            raw = self.rfile.read(length)
        except OSError:  # includes the socket timeout for a half-sent body
            self.close_connection = True
            return None
        if len(raw) < length:
            return None
        try:
            data = json.loads(raw.decode("utf-8"))
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
        session_id = data.get("session_id")
        session_id = session_id if isinstance(session_id, str) and SESSION_ID_RE.match(session_id) else None
        if self.path == "/api/reset":
            if session_id:
                with _session_lock(session_id), closing(storage.connect(self.db_path)) as conn:
                    storage.delete(conn, session_id)
            self._json(200, {"status": "cleared"})
            return
        if self.path != "/api/chat":
            self._json(404, {"error": "Not found."})
            return
        # One connection per request. Only ids the server issued earlier are accepted;
        # a made-up id gets a fresh session (no session fixation).
        lock = _session_lock(session_id) if session_id else threading.Lock()  # new students never wait for each other
        with closing(storage.connect(self.db_path)) as conn, lock:
            session = storage.load(conn, session_id) if session_id else None
            if session is None:
                session_id, session = uuid.uuid4().hex, Session()
            try:
                result = process_request(data.get("message"), session, provider=self.provider)
                storage.save(conn, session_id, session)
            except ValueError as exc:
                self._json(400, {"error": str(exc), "session_id": session_id})
                return
            except Exception:  # noqa: BLE001 - never leak internals to the page
                traceback.print_exc()
                self._json(500, {"error": "Something went wrong while handling that message. Try again.", "session_id": session_id})
                return
        self._json(200, {"session_id": session_id, **result})


def make_server(host: str = "127.0.0.1", port: int = 8000, db_path: str | None = None) -> ThreadingHTTPServer:
    Handler.db_path = db_path or os.environ.get("ASSISTANT_DB") or DATA_DIR / "assistant.db"
    storage.connect(Handler.db_path).close()  # create the tables now, fail fast on a bad path
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
    if sys.stdout is None or sys.stderr is None:
        # pythonw.exe (no console) sets these to None; http.server's request log would then
        # crash every request with an empty response. Send all output to a log file instead.
        log = open(DATA_DIR / "server.log", "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        sys.stdout = sys.stdout or log
        sys.stderr = sys.stderr or log
    server = make_server(args.host, args.port)
    ai = Handler.provider.name if Handler.provider else "off (rule-based only)"
    print(f"Student Learning Assistant running at http://{args.host}:{args.port}  (AI provider: {ai}, database: {Handler.db_path})")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
