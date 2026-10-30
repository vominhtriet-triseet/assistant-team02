import json
import threading
import urllib.error
import urllib.request

import pytest

from assistant.server import make_server


@pytest.fixture(scope="module")
def base_url():
    server = make_server("127.0.0.1", 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def post(url, payload):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read())


def test_chat_page_is_served(base_url):
    with urllib.request.urlopen(base_url + "/") as response:
        assert b"Student Learning Assistant" in response.read()


def test_health(base_url):
    with urllib.request.urlopen(base_url + "/api/health") as response:
        assert json.loads(response.read())["status"] == "ok"


def test_session_is_kept_between_messages(base_url):
    status, first = post(base_url + "/api/chat", {"message": "essay due Friday"})
    assert status == 200 and first["intent"] == "clarification"
    status, second = post(base_url + "/api/chat", {"message": "3 hours", "session_id": first["session_id"]})
    assert second["session_id"] == first["session_id"] and second["schedule"]


def test_empty_message_is_rejected(base_url):
    status, body = post(base_url + "/api/chat", {"message": "  "})
    assert status == 400 and body["error"] == "Please type a request."


def test_bad_json_is_rejected(base_url):
    request = urllib.request.Request(base_url + "/api/chat", data=b"not json", headers={"Content-Type": "application/json"})
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(request)
    assert err.value.code == 400
