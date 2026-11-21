"""Regression tests for the problems found by the penetration test (BUG-04 .. BUG-07)."""
import json
import socket
import threading
import time
import urllib.request

import pytest

from assistant.server import Handler, make_server


@pytest.fixture
def srv(tmp_path, monkeypatch):
    monkeypatch.setattr(Handler, "timeout", 1)  # keep the slow-body test short
    server = make_server("127.0.0.1", 0, db_path=str(tmp_path / "sec.db"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield server.server_address[1]
    server.shutdown()
    server.server_close()


def raw(port, data, wait=5):
    s = socket.create_connection(("127.0.0.1", port), timeout=wait)
    s.sendall(data)
    out = b""
    try:
        while chunk := s.recv(4096):
            out += chunk
    except (TimeoutError, socket.timeout):
        out += b"<<open>>"
    s.close()
    return out


def chat(port, payload):
    req = urllib.request.Request(f"http://127.0.0.1:{port}/api/chat", json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()), r.headers


def test_malformed_content_length_gets_400(srv):
    assert b" 400 " in raw(srv, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Length: abc\r\n\r\n{}")[:20]


def test_slow_body_is_dropped(srv):
    start = time.time()
    out = raw(srv, b"POST /api/chat HTTP/1.1\r\nHost: x\r\nContent-Length: 100\r\n\r\n{", wait=5)
    assert b"<<open>>" not in out and time.time() - start < 4


def test_unknown_session_id_is_replaced(srv):
    body, _ = chat(srv, {"message": "hello", "session_id": "ab" * 16})
    assert body["session_id"] != "ab" * 16
    again, _ = chat(srv, {"message": "hello", "session_id": body["session_id"]})
    assert again["session_id"] == body["session_id"]  # an id the server issued keeps working


def test_security_headers(srv):
    with urllib.request.urlopen(f"http://127.0.0.1:{srv}/") as r:
        headers = r.headers
    assert headers["X-Content-Type-Options"] == "nosniff" and headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"] and headers["Referrer-Policy"] == "no-referrer"
    assert "Python" not in headers["Server"]
